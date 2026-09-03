def signup(client, email="gwuser@example.com", password="correcthorsebatterystaple"):
    return client.post("/auth/signup", json={"email": email, "password": password})


def login(client, email="gwuser@example.com", password="correcthorsebatterystaple"):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_signup_is_public_and_proxies_through(client):
    response = signup(client)
    assert response.status_code == 201
    assert response.json()["email"] == "gwuser@example.com"


def test_login_is_public_and_proxies_through(client):
    signup(client)
    response = login(client)
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_me_without_token_rejected_at_gateway(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_garbage_token_rejected_at_gateway(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_me_with_valid_token_proxies_through(client):
    signup_body = signup(client).json()
    tokens = login(client).json()

    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == signup_body["id"]
    assert response.json()["email"] == signup_body["email"]


def test_path_not_in_public_set_requires_auth_even_if_it_starts_with_auth(client):
    # /auth/signup/extra isn't a real Auth route, but it isn't in
    # PUBLIC_PATHS either — it must be rejected for missing auth *before*
    # ever being forwarded, not treated as public just because it shares
    # the "/auth" prefix with a real public path.
    response = client.post("/auth/signup/extra", json={})
    assert response.status_code == 401


def test_unknown_route_returns_404(client):
    # Must stay a prefix genuinely absent from ROUTES, not just unused
    # today — /items and /board both started this way and later became
    # real routes, breaking this test each time (see git history). Pick
    # something that will never be a real backend's namespace.
    response = client.get("/nonexistent-service/whatever")
    assert response.status_code == 404


def test_path_sharing_a_prefix_without_boundary_returns_404_not_500(client):
    # /itemsxyz starts with the "/items" prefix as a raw string, but isn't
    # actually under that namespace — must not be misrouted (regression
    # test for a real bug: plain startswith() matched this and produced a
    # malformed target URL, crashing with a 500 instead of a clean 404).
    response = client.get("/itemsxyz")
    assert response.status_code == 404

    response = client.get("/boardish")
    assert response.status_code == 404


def test_logout_is_public_and_revokes_via_proxy(client):
    signup(client)
    tokens = login(client).json()

    logout_response = client.post(
        "/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401


def test_items_ingest_without_token_rejected_at_gateway(client):
    # Proves Decision #31 for real with a second backend, not just Auth:
    # Gateway's own logic didn't change to add Items, only the routing
    # table did.
    response = client.post(
        "/items",
        json={
            "source": "chrome",
            "external_id": "x1",
            "title": "t",
            "url": "https://example.com",
            "saved_at": "2026-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 401


def test_items_ingest_and_list_proxy_through_gateway(client):
    signup(client)
    tokens = login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    ingest_response = client.post(
        "/items",
        json={
            "source": "chrome",
            "external_id": "x1",
            "title": "Example",
            "url": "https://example.com",
            "saved_at": "2026-01-01T00:00:00Z",
        },
        headers=headers,
    )
    assert ingest_response.status_code == 201

    list_response = client.get("/items", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["external_id"] == "x1"


def test_board_create_without_token_rejected_at_gateway(client):
    # Third proof of Decision #31, alongside Items — Board too is just a
    # new routing-table row.
    response = client.post("/board", json={"name": "x"})
    assert response.status_code == 401


def test_board_create_and_add_item_proxy_through_gateway(client):
    signup(client)
    tokens = login(client).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    item = client.post(
        "/items",
        json={
            "source": "chrome",
            "external_id": "b1",
            "title": "Example",
            "url": "https://example.com",
            "saved_at": "2026-01-01T00:00:00Z",
        },
        headers=headers,
    ).json()

    board = client.post("/board", json={"name": "Shared via Gateway"}, headers=headers)
    assert board.status_code == 201
    board_id = board.json()["id"]

    add_response = client.post(
        f"/board/{board_id}/items", json={"item_id": item["id"]}, headers=headers
    )
    assert add_response.status_code == 201

    view_response = client.get(f"/board/{board_id}", headers=headers)
    assert view_response.status_code == 200
    assert len(view_response.json()["items"]) == 1
