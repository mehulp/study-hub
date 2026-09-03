def create_board(client, headers, name="Test Board"):
    return client.post("/", json={"name": name}, headers=headers)


def test_create_board_without_token_rejected(client):
    response = client.post("/", json={"name": "x"})
    assert response.status_code == 401


def test_create_board(client, owner_headers, owner_identity):
    response = create_board(client, owner_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Board"
    assert body["owner_user_id"] == owner_identity["user_id"]


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
