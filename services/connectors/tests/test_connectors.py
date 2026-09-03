import uuid

from datetime import datetime, timezone


def create_connection(client, headers, conn_type="browser_chrome"):
    return client.post("/connections", json={"type": conn_type}, headers=headers)


def bookmark(external_id=None, **overrides):
    payload = {
        "external_id": external_id or f"bm-{uuid.uuid4()}",
        "title": "Example",
        "url": "https://example.com",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_create_connection_without_token_rejected(client):
    response = client.post("/connections", json={"type": "browser_chrome"})
    assert response.status_code == 401


def test_create_connection(client, owner_headers):
    response = create_connection(client, owner_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "browser_chrome"
    assert len(body["push_token"]) >= 32
    assert body["last_synced_at"] is None


def test_list_connections_never_exposes_push_token(client, owner_headers):
    create_connection(client, owner_headers)
    response = client.get("/connections", headers=owner_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
    for connection in response.json():
        assert "push_token" not in connection


def test_list_connections_without_token_rejected(client):
    response = client.get("/connections")
    assert response.status_code == 401


def test_sync_without_token_rejected(client, owner_headers):
    connection = create_connection(client, owner_headers).json()
    response = client.post(f"/connections/{connection['id']}/sync", json={"items": []})
    assert response.status_code == 401


def test_sync_with_wrong_push_token_rejected(client, owner_headers):
    connection = create_connection(client, owner_headers).json()
    response = client.post(
        f"/connections/{connection['id']}/sync",
        json={"items": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 404


def test_sync_with_another_connections_push_token_rejected(client, owner_headers):
    connection_a = create_connection(client, owner_headers).json()
    connection_b = create_connection(client, owner_headers).json()

    # connection_a's id, but connection_b's push token — must not work.
    response = client.post(
        f"/connections/{connection_a['id']}/sync",
        json={"items": []},
        headers={"Authorization": f"Bearer {connection_b['push_token']}"},
    )
    assert response.status_code == 404


def test_sync_creates_items(client, owner_headers):
    connection = create_connection(client, owner_headers).json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}

    response = client.post(
        f"/connections/{connection['id']}/sync",
        json={"items": [bookmark(), bookmark()]},
        headers=push_headers,
    )
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    assert all(r["status"] == "created" for r in results)


def test_sync_is_idempotent_per_item(client, owner_headers):
    connection = create_connection(client, owner_headers).json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}
    item = bookmark()

    first = client.post(
        f"/connections/{connection['id']}/sync", json={"items": [item]}, headers=push_headers
    )
    second = client.post(
        f"/connections/{connection['id']}/sync", json={"items": [item]}, headers=push_headers
    )
    assert first.json()["results"][0]["status"] == "created"
    assert second.json()["results"][0]["status"] == "already_exists"


def test_sync_updates_last_synced_at(client, owner_headers):
    connection = create_connection(client, owner_headers).json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}

    client.post(
        f"/connections/{connection['id']}/sync", json={"items": [bookmark()]}, headers=push_headers
    )

    response = client.get("/connections", headers=owner_headers)
    synced = next(c for c in response.json() if c["id"] == connection["id"])
    assert synced["last_synced_at"] is not None


def test_sync_lands_items_under_the_connection_owner(client, owner_headers, owner_identity):
    import httpx

    from tests.conftest import ITEMS_TEST_URL

    connection = create_connection(client, owner_headers).json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}
    item = bookmark()

    client.post(
        f"/connections/{connection['id']}/sync", json={"items": [item]}, headers=push_headers
    )

    items_response = httpx.get(f"{ITEMS_TEST_URL}/", headers=owner_headers)
    external_ids = {i["external_id"] for i in items_response.json()}
    assert item["external_id"] in external_ids


def test_sync_maps_connection_type_to_source(client, owner_headers, owner_identity):
    import httpx

    from tests.conftest import ITEMS_TEST_URL

    connection = create_connection(client, owner_headers, conn_type="browser_firefox").json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}
    item = bookmark()

    client.post(
        f"/connections/{connection['id']}/sync", json={"items": [item]}, headers=push_headers
    )

    items_response = httpx.get(f"{ITEMS_TEST_URL}/", headers=owner_headers)
    synced_item = next(i for i in items_response.json() if i["external_id"] == item["external_id"])
    assert synced_item["source"] == "firefox"


def test_sync_partial_failure_does_not_block_other_items(client, owner_headers, monkeypatch):
    import app.main as connectors_main
    from app.items_client import ItemsServiceError

    connection = create_connection(client, owner_headers).json()
    push_headers = {"Authorization": f"Bearer {connection['push_token']}"}

    call_count = 0

    async def flaky_ingest_item(owner_user_id, item):
        nonlocal call_count
        call_count += 1
        if item["external_id"] == "will-fail":
            raise ItemsServiceError("simulated outage")
        return 201, {}

    monkeypatch.setattr(connectors_main, "ingest_item", flaky_ingest_item)

    response = client.post(
        f"/connections/{connection['id']}/sync",
        json={"items": [bookmark(external_id="will-fail"), bookmark(external_id="will-succeed")]},
        headers=push_headers,
    )
    assert response.status_code == 200
    results = {r["external_id"]: r["status"] for r in response.json()["results"]}
    assert results["will-fail"] == "error"
    assert results["will-succeed"] == "created"
