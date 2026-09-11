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


def test_ingest_via_service_token_requires_owner_user_id(client, service_headers):
    response = client.post("/", json=ingest_payload(), headers=service_headers)
    assert response.status_code == 400


def test_ingest_via_service_token_with_owner_user_id(client, service_headers, auth_identity):
    response = client.post(
        "/",
        json=ingest_payload(owner_user_id=auth_identity["user_id"]),
        headers=service_headers,
    )
    assert response.status_code == 201
    assert response.json()["owner_user_id"] == auth_identity["user_id"]


def test_ingest_via_service_token_lands_in_owners_own_list(
    client, service_headers, auth_headers, auth_identity
):
    client.post(
        "/",
        json=ingest_payload(external_id="via-connector", owner_user_id=auth_identity["user_id"]),
        headers=service_headers,
    )

    response = client.get("/", headers=auth_headers)
    assert response.status_code == 200
    external_ids = {item["external_id"] for item in response.json()}
    assert "via-connector" in external_ids


def test_user_token_ingest_ignores_spoofed_owner_user_id(client, auth_headers, auth_identity):
    other_user_id = str(uuid.uuid4())
    response = client.post(
        "/",
        json=ingest_payload(external_id="spoof-attempt", owner_user_id=other_user_id),
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["owner_user_id"] == auth_identity["user_id"]
    assert response.json()["owner_user_id"] != other_user_id


def test_service_token_rejected_by_list(client, service_headers):
    response = client.get("/", headers=service_headers)
    assert response.status_code == 401


def test_service_token_rejected_by_get_item(client, service_headers):
    response = client.get(
        "/00000000-0000-0000-0000-000000000000", headers=service_headers
    )
    assert response.status_code == 401


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
    client.post("/", json=ingest_payload(source="manual", external_id="https://example.com/m1"), headers=auth_headers)

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


def test_ingest_with_notes_and_tags(client, auth_headers):
    response = client.post(
        "/",
        json=ingest_payload(notes="Great refresher", tags=["System Design", "Distributed-Systems"]),
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["notes"] == "Great refresher"
    assert sorted(body["tags"]) == ["distributed-systems", "system design"]


def test_ingest_tags_deduplicated_after_lowercasing(client, auth_headers):
    response = client.post(
        "/",
        json=ingest_payload(tags=["System Design", "system design", " System Design "]),
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["system design"]


def test_patch_updates_title_and_url(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()

    response = client.patch(
        f"/{created['id']}",
        json={"title": "New Title", "url": "https://example.com/new"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New Title"
    assert body["url"] == "https://example.com/new"


def test_patch_partial_update_leaves_other_fields_unchanged(client, auth_headers):
    created = client.post("/", json=ingest_payload(notes="original notes"), headers=auth_headers).json()

    response = client.patch(f"/{created['id']}", json={"title": "Only Title Changed"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Only Title Changed"
    assert body["notes"] == "original notes"
    assert body["url"] == created["url"]


def test_patch_explicit_null_clears_notes(client, auth_headers):
    created = client.post("/", json=ingest_payload(notes="will be cleared"), headers=auth_headers).json()
    assert created["notes"] == "will be cleared"

    response = client.patch(f"/{created['id']}", json={"notes": None}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["notes"] is None


def test_patch_sets_preview_media_url(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()
    assert created["preview_media_url"] is None

    response = client.patch(
        f"/{created['id']}",
        json={"preview_media_url": "https://pbs.twimg.com/media/example.jpg"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["preview_media_url"] == "https://pbs.twimg.com/media/example.jpg"


def test_patch_explicit_null_clears_preview_media_url(client, auth_headers):
    created = client.post(
        "/", json=ingest_payload(preview_media_url="https://pbs.twimg.com/media/example.jpg"), headers=auth_headers
    ).json()
    assert created["preview_media_url"] == "https://pbs.twimg.com/media/example.jpg"

    response = client.patch(f"/{created['id']}", json={"preview_media_url": None}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["preview_media_url"] is None


def test_patch_replaces_tags(client, auth_headers):
    created = client.post("/", json=ingest_payload(tags=["old-tag"]), headers=auth_headers).json()

    response = client.patch(f"/{created['id']}", json={"tags": ["new-tag", "another"]}, headers=auth_headers)
    assert response.status_code == 200
    assert sorted(response.json()["tags"]) == ["another", "new-tag"]


def test_patch_empty_tags_list_clears_all_tags(client, auth_headers):
    created = client.post("/", json=ingest_payload(tags=["a", "b"]), headers=auth_headers).json()

    response = client.patch(f"/{created['id']}", json={"tags": []}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_patch_null_title_rejected(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()

    response = client.patch(f"/{created['id']}", json={"title": None}, headers=auth_headers)
    assert response.status_code == 400


def test_patch_nonexistent_item_returns_404(client, auth_headers):
    response = client.patch("/00000000-0000-0000-0000-000000000000", json={"title": "x"}, headers=auth_headers)
    assert response.status_code == 404


def test_patch_without_token_rejected(client):
    response = client.patch("/00000000-0000-0000-0000-000000000000", json={"title": "x"})
    assert response.status_code == 401


def test_delete_item_removes_it(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()

    response = client.delete(f"/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_cascades_tags(client, auth_headers, db_session):
    from app.models import ItemTag

    created = client.post("/", json=ingest_payload(tags=["cascade-me"]), headers=auth_headers).json()

    response = client.delete(f"/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    remaining = db_session.query(ItemTag).filter(ItemTag.item_id == created["id"]).count()
    assert remaining == 0


def test_delete_nonexistent_item_returns_404(client, auth_headers):
    response = client.delete("/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


def test_delete_without_token_rejected(client):
    response = client.delete("/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


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
                "psql", "-U", "study_hub", "-d", "study_hub_test",
                "-c", f"DELETE FROM auth.refresh_tokens WHERE user_id = '{other_user_id}'; "
                      f"DELETE FROM auth.users WHERE id = '{other_user_id}';",
            ],
            cwd=Path(__file__).resolve().parent.parent.parent.parent,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _create_other_user(client, created_item_id, verb):
    """Shared shape for the PATCH/DELETE ownership-scoping tests below —
    same real-second-account pattern as test_get_item_belonging_to_another_user_returns_404."""
    other_email = f"items-test-other-user-{uuid.uuid4()}@example.com"
    other_password = "correcthorsebatterystaple"
    signup = httpx.post(f"{AUTH_TEST_URL}/signup", json={"email": other_email, "password": other_password})
    other_user_id = signup.json()["id"]
    other_login = httpx.post(f"{AUTH_TEST_URL}/login", json={"email": other_email, "password": other_password})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    try:
        if verb == "patch":
            response = client.patch(f"/{created_item_id}", json={"title": "hijacked"}, headers=other_headers)
        else:
            response = client.delete(f"/{created_item_id}", headers=other_headers)
        assert response.status_code == 404
    finally:
        subprocess.run(
            [
                "docker", "compose", "exec", "-T", "postgres",
                "psql", "-U", "study_hub", "-d", "study_hub_test",
                "-c", f"DELETE FROM auth.refresh_tokens WHERE user_id = '{other_user_id}'; "
                      f"DELETE FROM auth.users WHERE id = '{other_user_id}';",
            ],
            cwd=Path(__file__).resolve().parent.parent.parent.parent,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def test_patch_item_belonging_to_another_user_returns_404(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()
    _create_other_user(client, created["id"], "patch")

    # Confirm the hijack attempt didn't actually apply.
    still_owned = client.get(f"/{created['id']}", headers=auth_headers)
    assert still_owned.json()["title"] != "hijacked"


def test_delete_item_belonging_to_another_user_returns_404(client, auth_headers):
    created = client.post("/", json=ingest_payload(), headers=auth_headers).json()
    _create_other_user(client, created["id"], "delete")

    # Confirm the item is still there, not actually deleted.
    still_there = client.get(f"/{created['id']}", headers=auth_headers)
    assert still_there.status_code == 200
