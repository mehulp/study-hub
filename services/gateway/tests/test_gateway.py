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
    # /items is now a real registered route (Items service) — use a prefix
    # genuinely absent from ROUTES so this still tests an actual no-match,
    # not the auth check on a route that does exist.
    response = client.get("/board/whatever")
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
