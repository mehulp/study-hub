import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from tests.conftest import AUTH_TEST_URL


def ingest_payload(source="chrome", external_id="abc123", **overrides):
    payload = {
        "source": source,
        "external_id": external_id,
        "title": "Example",
        "url": "https://example.com",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_ingest_without_token_rejected(client):
    response = client.post("/", json=ingest_payload())
    assert response.status_code == 401


def test_ingest_creates_item(client, auth_headers, auth_identity):
    response = client.post("/", json=ingest_payload(), headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["owner_user_id"] == auth_identity["user_id"]
    assert body["source"] == "chrome"
    assert body["title"] == "Example"


def test_ingest_duplicate_is_idempotent(client, auth_headers):
    first = client.post("/", json=ingest_payload(), headers=auth_headers)
    second = client.post("/", json=ingest_payload(), headers=auth_headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_ingest_same_external_id_different_source_is_distinct(client, auth_headers):
    chrome_item = client.post(
        "/", json=ingest_payload(source="chrome", external_id="shared-id"), headers=auth_headers
    )
    firefox_item = client.post(
        "/", json=ingest_payload(source="firefox", external_id="shared-id"), headers=auth_headers
    )

    assert chrome_item.status_code == 201
    assert firefox_item.status_code == 201
    assert chrome_item.json()["id"] != firefox_item.json()["id"]


def test_list_items_without_token_rejected(client):
    response = client.get("/")
    assert response.status_code == 401


def test_list_items_returns_ingested_items(client, auth_headers):
    client.post("/", json=ingest_payload(external_id="one"), headers=auth_headers)
    client.post("/", json=ingest_payload(external_id="two"), headers=auth_headers)

    response = client.get("/", headers=auth_headers)
    assert response.status_code == 200
    external_ids = {item["external_id"] for item in response.json()}
    assert external_ids == {"one", "two"}


def test_list_items_filtered_by_source(client, auth_headers):
    client.post("/", json=ingest_payload(source="chrome", external_id="c1"), headers=auth_headers)
    client.post("/", json=ingest_payload(source="twitter", external_id="t1"), headers=auth_headers)

    response = client.get("/?source=chrome", headers=auth_headers)
    assert response.status_code == 200
    sources = {item["source"] for item in response.json()}
    assert sources == {"chrome"}


def test_get_item_by_id(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()

    response = client.get(f"/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_item_returns_404(client, auth_headers):
    response = client.get(
        "/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404


def test_get_item_belonging_to_another_user_returns_404(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()

    other_email = f"items-test-other-user-{uuid.uuid4()}@example.com"
    other_password = "correcthorsebatterystaple"
    signup = httpx.post(
        f"{AUTH_TEST_URL}/signup", json={"email": other_email, "password": other_password}
    )
    other_user_id = signup.json()["id"]
    other_login = httpx.post(
        f"{AUTH_TEST_URL}/login", json={"email": other_email, "password": other_password}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    try:
        response = client.get(f"/{created['id']}", headers=other_headers)
        assert response.status_code == 404
    finally:
        subprocess.run(
            [
                "docker", "compose", "exec", "-T", "postgres",
                "psql", "-U", "bookmarks_hub", "-d", "bookmarks_hub_test",
                "-c", f"DELETE FROM auth.refresh_tokens WHERE user_id = '{other_user_id}'; "
                      f"DELETE FROM auth.users WHERE id = '{other_user_id}';",
            ],
            cwd=Path(__file__).resolve().parent.parent.parent.parent,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
