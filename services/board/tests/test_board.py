def create_board(client, headers, name="Test Board"):
    return client.post("/", json={"name": name}, headers=headers)


def invite_and_accept(client, owner_headers, other_headers, invited_email, board=None):
    """Creates a board (unless given one), invites invited_email, and
    accepts as the user behind other_headers. Returns (board, accept_response)."""
    if board is None:
        board = create_board(client, owner_headers).json()

    invite = client.post(
        f"/{board['id']}/invite", json={"invited_email": invited_email}, headers=owner_headers
    )
    token = invite.json()["invite_token"]

    accept_response = client.post(f"/invites/{token}/accept", headers=other_headers)
    return board, accept_response


def test_create_board_without_token_rejected(client):
    response = client.post("/", json={"name": "x"})
    assert response.status_code == 401


def test_create_board(client, owner_headers, owner_identity):
    response = create_board(client, owner_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Board"
    assert body["owner_user_id"] == owner_identity["user_id"]
    assert body["owner_email"] == owner_identity["email"]
    # owner_identity signs up without first_name (matches every other
    # service's test fixtures, Decision #73) -- confirms the field is
    # honestly null, not silently defaulted to something else.
    assert body["owner_first_name"] is None


def test_create_board_includes_owner_first_name_when_set(client):
    from tests.conftest import _create_real_user, _delete_user

    named_owner = _create_real_user(first_name="Priya")
    try:
        headers = {"Authorization": f"Bearer {named_owner['access_token']}"}
        response = create_board(client, headers)
        assert response.status_code == 201
        assert response.json()["owner_first_name"] == "Priya"
    finally:
        _delete_user(named_owner["user_id"])


def test_get_board_as_owner(client, owner_headers):
    board = create_board(client, owner_headers).json()

    response = client.get(f"/{board['id']}", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "owner"
    assert body["items"] == []


def test_get_nonexistent_board_returns_404(client, owner_headers):
    response = client.get(
        "/00000000-0000-0000-0000-000000000000", headers=owner_headers
    )
    assert response.status_code == 404


def test_get_board_with_no_access_returns_404(client, owner_headers, other_headers):
    board = create_board(client, owner_headers).json()

    response = client.get(f"/{board['id']}", headers=other_headers)
    assert response.status_code == 404


def test_add_item_to_board(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()

    response = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )
    assert response.status_code == 201
    assert response.json()["item_id"] == ingested_item["id"]
    assert response.json()["title"] == ingested_item["title"]


def test_add_item_returns_503_when_items_service_fails(
    client, owner_headers, ingested_item, monkeypatch
):
    # Regression test: fetch_item raising ItemsServiceError (Items down,
    # timed out, or erroring) used to propagate as an unhandled exception
    # (a bare 500) instead of a coherent response.
    import app.main as board_main
    from app.items_client import ItemsServiceError

    async def broken_fetch_item(item_id, bearer_token):
        raise ItemsServiceError("simulated outage")

    monkeypatch.setattr(board_main, "fetch_item", broken_fetch_item)

    board = create_board(client, owner_headers).json()
    response = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )
    assert response.status_code == 503


def test_add_item_is_idempotent(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()

    first = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )
    second = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )
    assert first.status_code == 201
    assert second.status_code == 200


def test_add_item_denormalizes_display_fields(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )

    view = client.get(f"/{board['id']}", headers=owner_headers).json()
    assert len(view["items"]) == 1
    assert view["items"][0]["url"] == ingested_item["url"]
    assert view["items"][0]["favicon_url"] == ingested_item["favicon_url"]


def test_add_item_snapshots_tags(client, owner_headers, ingested_item_with_tags):
    board = create_board(client, owner_headers).json()
    response = client.post(
        f"/{board['id']}/items",
        json={"item_id": ingested_item_with_tags["id"]},
        headers=owner_headers,
    )
    assert sorted(response.json()["tags"]) == ["databases", "system-design"]

    view = client.get(f"/{board['id']}", headers=owner_headers).json()
    assert sorted(view["items"][0]["tags"]) == ["databases", "system-design"]


def test_add_nonexistent_item_returns_404(client, owner_headers):
    board = create_board(client, owner_headers).json()

    response = client.post(
        f"/{board['id']}/items",
        json={"item_id": "00000000-0000-0000-0000-000000000000"},
        headers=owner_headers,
    )
    assert response.status_code == 404


def test_non_owner_cannot_add_item(client, owner_headers, other_headers, ingested_item):
    board = create_board(client, owner_headers).json()

    response = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=other_headers
    )
    assert response.status_code == 404


def test_other_users_item_cannot_be_added_to_your_board(client, owner_headers, other_headers, other_user):
    # ingested_item belongs to owner_identity; here we ingest one that
    # belongs to other_user instead, then try to add it to owner's board.
    import httpx

    from tests.conftest import ITEMS_TEST_URL

    foreign_item = httpx.post(
        f"{ITEMS_TEST_URL}/",
        json={
            "source": "chrome",
            "external_id": "foreign-1",
            "title": "Not yours",
            "url": "https://example.com",
            "saved_at": "2026-01-01T00:00:00Z",
        },
        headers=other_headers,
    ).json()

    board = create_board(client, owner_headers).json()
    response = client.post(
        f"/{board['id']}/items", json={"item_id": foreign_item["id"]}, headers=owner_headers
    )
    assert response.status_code == 404


def test_remove_item(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )

    response = client.delete(f"/{board['id']}/items/{ingested_item['id']}", headers=owner_headers)
    assert response.status_code == 204

    view = client.get(f"/{board['id']}", headers=owner_headers).json()
    assert view["items"] == []


def test_remove_item_is_idempotent(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()

    first = client.delete(f"/{board['id']}/items/{ingested_item['id']}", headers=owner_headers)
    second = client.delete(f"/{board['id']}/items/{ingested_item['id']}", headers=owner_headers)
    assert first.status_code == 204
    assert second.status_code == 204


def test_non_owner_cannot_remove_item(client, owner_headers, other_headers, ingested_item):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )

    response = client.delete(f"/{board['id']}/items/{ingested_item['id']}", headers=other_headers)
    assert response.status_code == 404


def test_create_invite_without_token_rejected(client, owner_headers):
    board = create_board(client, owner_headers).json()
    response = client.post(f"/{board['id']}/invite", json={"invited_email": "x@example.com"})
    assert response.status_code == 401


def test_create_invite_by_non_owner_with_no_access_returns_404(client, owner_headers, other_headers):
    board = create_board(client, owner_headers).json()
    response = client.post(
        f"/{board['id']}/invite", json={"invited_email": "x@example.com"}, headers=other_headers
    )
    assert response.status_code == 404


def test_create_invite_success(client, owner_headers):
    board = create_board(client, owner_headers).json()
    response = client.post(
        f"/{board['id']}/invite", json={"invited_email": "someone@example.com"}, headers=owner_headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["board_id"] == board["id"]
    assert body["invited_email"] == "someone@example.com"
    assert body["role"] == "viewer"
    assert len(body["invite_token"]) >= 32


def test_create_invite_rejects_duplicate_pending_invite_for_same_email(client, owner_headers):
    board = create_board(client, owner_headers).json()
    first = client.post(
        f"/{board['id']}/invite", json={"invited_email": "someone@example.com"}, headers=owner_headers
    )
    assert first.status_code == 201

    second = client.post(
        f"/{board['id']}/invite", json={"invited_email": "someone@example.com"}, headers=owner_headers
    )
    assert second.status_code == 409

    # Case-insensitivity: same email, different casing, still rejected.
    third = client.post(
        f"/{board['id']}/invite", json={"invited_email": "SOMEONE@example.com"}, headers=owner_headers
    )
    assert third.status_code == 409


def test_create_invite_rejects_duplicate_after_acceptance(
    client, owner_headers, other_headers, other_user
):
    board, accept_response = invite_and_accept(
        client, owner_headers, other_headers, other_user["email"]
    )
    assert accept_response.status_code == 200

    response = client.post(
        f"/{board['id']}/invite", json={"invited_email": other_user["email"]}, headers=owner_headers
    )
    assert response.status_code == 409


def test_create_invite_allows_different_emails_on_same_board(client, owner_headers):
    board = create_board(client, owner_headers).json()
    first = client.post(
        f"/{board['id']}/invite", json={"invited_email": "one@example.com"}, headers=owner_headers
    )
    second = client.post(
        f"/{board['id']}/invite", json={"invited_email": "two@example.com"}, headers=owner_headers
    )
    assert first.status_code == 201
    assert second.status_code == 201


def test_accept_invite_grants_viewer_access(client, owner_headers, other_headers, other_user):
    board, accept_response = invite_and_accept(
        client, owner_headers, other_headers, other_user["email"]
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["role"] == "viewer"
    assert accept_response.json()["id"] == board["id"]


def test_viewer_can_view_board_directly_after_accepting(client, owner_headers, other_headers, other_user):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])

    response = client.get(f"/{board['id']}", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "viewer"


def test_accept_invite_is_idempotent_for_same_user(client, owner_headers, other_headers, other_user):
    board = create_board(client, owner_headers).json()
    invite = client.post(
        f"/{board['id']}/invite", json={"invited_email": other_user["email"]}, headers=owner_headers
    )
    token = invite.json()["invite_token"]

    first = client.post(f"/invites/{token}/accept", headers=other_headers)
    second = client.post(f"/invites/{token}/accept", headers=other_headers)
    assert first.status_code == 200
    assert second.status_code == 200


def test_accept_invite_rejected_for_different_user_once_claimed(
    client, owner_headers, other_headers, other_user
):
    from tests.conftest import _create_real_user, _delete_user

    board = create_board(client, owner_headers).json()
    invite = client.post(
        f"/{board['id']}/invite", json={"invited_email": other_user["email"]}, headers=owner_headers
    )
    token = invite.json()["invite_token"]

    client.post(f"/invites/{token}/accept", headers=other_headers)

    intruder = _create_real_user()
    try:
        intruder_headers = {"Authorization": f"Bearer {intruder['access_token']}"}
        response = client.post(f"/invites/{token}/accept", headers=intruder_headers)
        assert response.status_code == 404
    finally:
        _delete_user(intruder["user_id"])


def test_accept_unknown_token_returns_404(client, other_headers):
    response = client.post("/invites/not-a-real-token/accept", headers=other_headers)
    assert response.status_code == 404


def test_viewer_cannot_add_items(client, owner_headers, other_headers, other_user, ingested_item):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])

    response = client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=other_headers
    )
    assert response.status_code == 403


def test_viewer_cannot_remove_items(client, owner_headers, other_headers, other_user, ingested_item):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])
    client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )

    response = client.delete(f"/{board['id']}/items/{ingested_item['id']}", headers=other_headers)
    assert response.status_code == 403


def test_viewer_cannot_invite_others(client, owner_headers, other_headers, other_user):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])

    response = client.post(
        f"/{board['id']}/invite", json={"invited_email": "third@example.com"}, headers=other_headers
    )
    assert response.status_code == 403


def test_list_my_boards_without_token_rejected(client):
    response = client.get("/mine")
    assert response.status_code == 401


def test_list_my_boards_empty_when_none_owned(client, owner_headers):
    response = client.get("/mine", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_my_boards_excludes_other_users_boards(client, owner_headers, other_headers):
    create_board(client, other_headers, name="Not Yours")

    response = client.get("/mine", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_my_boards_returns_item_count(client, owner_headers, ingested_item):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/items", json={"item_id": ingested_item["id"]}, headers=owner_headers
    )

    response = client.get("/mine", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == board["id"]
    assert body[0]["item_count"] == 1


def test_list_my_boards_includes_grants(client, owner_headers, other_headers, other_user):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])

    response = client.get("/mine", headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert len(body[0]["grants"]) == 1
    grant = body[0]["grants"][0]
    assert grant["invited_email"] == other_user["email"]
    assert grant["status"] == "accepted"
    assert grant["role"] == "viewer"
    assert grant["accepted_at"] is not None


def test_list_my_boards_shows_pending_grant_before_acceptance(client, owner_headers):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/invite", json={"invited_email": "someone@example.com"}, headers=owner_headers
    )

    response = client.get("/mine", headers=owner_headers)
    grant = response.json()[0]["grants"][0]
    assert grant["status"] == "pending"
    assert grant["accepted_at"] is None


def test_list_shared_with_me_without_token_rejected(client):
    response = client.get("/shared-with-me")
    assert response.status_code == 401


def test_list_shared_with_me_empty_when_no_accepted_invites(client, other_headers):
    response = client.get("/shared-with-me", headers=other_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_shared_with_me_excludes_pending_invites(client, owner_headers, other_headers):
    board = create_board(client, owner_headers).json()
    client.post(
        f"/{board['id']}/invite", json={"invited_email": "not-accepted-yet@example.com"}, headers=owner_headers
    )

    # other_headers' user never accepted anything -- should see nothing.
    response = client.get("/shared-with-me", headers=other_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_shared_with_me_returns_accepted_boards(client, owner_headers, other_headers, other_user, owner_identity):
    board, _ = invite_and_accept(client, owner_headers, other_headers, other_user["email"])

    response = client.get("/shared-with-me", headers=other_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == board["id"]
    assert body[0]["name"] == board["name"]
    assert body[0]["role"] == "viewer"
    assert body[0]["item_count"] == 0
    assert body[0]["owner_email"] == owner_identity["email"]


def test_list_shared_with_me_includes_owner_first_name(client, other_headers, other_user):
    from tests.conftest import _create_real_user, _delete_user

    named_owner = _create_real_user(first_name="Priya")
    try:
        named_owner_headers = {"Authorization": f"Bearer {named_owner['access_token']}"}
        board, _ = invite_and_accept(client, named_owner_headers, other_headers, other_user["email"])

        response = client.get("/shared-with-me", headers=other_headers)
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == board["id"]
        assert body[0]["owner_first_name"] == "Priya"
    finally:
        _delete_user(named_owner["user_id"])


def test_create_board_returns_503_when_auth_service_fails(client, owner_headers, monkeypatch):
    # Same shape as add_item's Items-unavailable handling: an unreachable
    # dependency must surface as a coherent 503, not a bare 500 or a board
    # silently created with no owner_email.
    import app.main as board_main
    from app.auth_client import AuthServiceError

    async def broken_fetch_own_identity(bearer_token):
        raise AuthServiceError("simulated outage")

    monkeypatch.setattr(board_main, "fetch_own_identity", broken_fetch_own_identity)

    response = client.post("/", json={"name": "x"}, headers=owner_headers)
    assert response.status_code == 503


def test_list_shared_with_me_excludes_boards_owned_by_the_viewer(client, owner_headers):
    create_board(client, owner_headers)

    response = client.get("/shared-with-me", headers=owner_headers)
    assert response.status_code == 200
    assert response.json() == []
