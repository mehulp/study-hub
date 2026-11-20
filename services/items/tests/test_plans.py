from datetime import datetime, timezone

import pytest


def ingest_payload(source="manual", external_id="plan-item-1", **overrides):
    payload = {
        "source": source,
        "external_id": external_id,
        "title": "Example Resource",
        "url": "https://example.com",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def create_item(client, headers, **overrides):
    return client.post("/", json=ingest_payload(**overrides), headers=headers).json()


def create_plan(client, headers, name="4-Week Prep", **overrides):
    body = {"name": name, **overrides}
    return client.post("/plans", json=body, headers=headers)


# ---------- Plan CRUD ----------


def test_create_plan_success(client, auth_headers):
    response = create_plan(client, auth_headers, description="System design fundamentals")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "4-Week Prep"
    assert body["description"] == "System design fundamentals"
    assert body["items"] == []


def test_create_plan_without_token_rejected(client):
    response = client.post("/plans", json={"name": "x"})
    assert response.status_code == 401


def test_create_plan_blank_name_rejected(client, auth_headers):
    response = create_plan(client, auth_headers, name="   ")
    assert response.status_code == 422


def test_list_plans_returns_only_own_plans(client, auth_headers, other_headers):
    create_plan(client, auth_headers, name="Mine")
    create_plan(client, other_headers, name="Not mine")

    response = client.get("/plans", headers=auth_headers)
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Mine" in names
    assert "Not mine" not in names


def test_get_plan_not_owned_returns_404(client, auth_headers, other_headers):
    plan = create_plan(client, other_headers).json()
    response = client.get(f"/plans/{plan['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_get_nonexistent_plan_returns_404(client, auth_headers):
    response = client.get("/plans/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


def test_update_plan_renames(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.patch(f"/plans/{plan['id']}", json={"name": "Renamed"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_update_plan_blank_name_rejected(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.patch(f"/plans/{plan['id']}", json={"name": "  "}, headers=auth_headers)
    assert response.status_code == 400


def test_delete_plan_success(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.delete(f"/plans/{plan['id']}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get(f"/plans/{plan['id']}", headers=auth_headers).status_code == 404


def test_delete_plan_does_not_delete_underlying_item(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    client.delete(f"/plans/{plan['id']}", headers=auth_headers)

    assert client.get(f"/{item['id']}", headers=auth_headers).status_code == 200


# ---------- Plan items ----------


def test_add_plan_item_success(client, auth_headers):
    item = create_item(client, auth_headers, title="Consistent Hashing", tags=["caching", "distributed-systems"])
    plan = create_plan(client, auth_headers).json()

    response = client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["item_id"] == item["id"]
    assert body["title"] == "Consistent Hashing"
    assert sorted(body["tags"]) == ["caching", "distributed-systems"]
    assert body["status"] == "not_started"


def test_add_plan_item_with_full_metadata(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()

    response = client.post(
        f"/plans/{plan['id']}/items",
        json={
            "item_id": item["id"],
            "status": "in_progress",
            "order_index": 1,
            "priority": "high",
            "target_date": "2026-10-01",
            "estimated_effort_minutes": 45,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["order_index"] == 1
    assert body["priority"] == "high"
    assert body["target_date"] == "2026-10-01"
    assert body["estimated_effort_minutes"] == 45


def test_add_plan_item_duplicate_returns_409(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    response = client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)
    assert response.status_code == 409


def test_add_plan_item_belonging_to_another_user_returns_404(client, auth_headers, other_headers):
    foreign_item = create_item(client, other_headers)
    plan = create_plan(client, auth_headers).json()

    response = client.post(
        f"/plans/{plan['id']}/items", json={"item_id": foreign_item["id"]}, headers=auth_headers
    )
    assert response.status_code == 404


def test_add_item_to_plan_not_owned_returns_404(client, auth_headers, other_headers):
    item = create_item(client, auth_headers)
    foreign_plan = create_plan(client, other_headers).json()

    response = client.post(
        f"/plans/{foreign_plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers
    )
    assert response.status_code == 404


def test_get_plan_includes_its_items(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    response = client.get(f"/plans/{plan['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["item_id"] == item["id"]


def test_update_plan_item_status(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    response = client.patch(
        f"/plans/{plan['id']}/items/{item['id']}", json={"status": "completed"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_update_plan_item_null_status_rejected(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    response = client.patch(
        f"/plans/{plan['id']}/items/{item['id']}", json={"status": None}, headers=auth_headers
    )
    assert response.status_code == 400


def test_update_plan_item_clears_priority_with_explicit_null(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(
        f"/plans/{plan['id']}/items",
        json={"item_id": item["id"], "priority": "high"},
        headers=auth_headers,
    )

    response = client.patch(
        f"/plans/{plan['id']}/items/{item['id']}", json={"priority": None}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["priority"] is None


def test_update_nonexistent_plan_item_returns_404(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.patch(
        f"/plans/{plan['id']}/items/00000000-0000-0000-0000-000000000000",
        json={"status": "completed"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_remove_plan_item_success(client, auth_headers):
    item = create_item(client, auth_headers)
    plan = create_plan(client, auth_headers).json()
    client.post(f"/plans/{plan['id']}/items", json={"item_id": item["id"]}, headers=auth_headers)

    response = client.delete(f"/plans/{plan['id']}/items/{item['id']}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get(f"/plans/{plan['id']}", headers=auth_headers).json()["items"] == []


def test_remove_nonexistent_plan_item_returns_404(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.delete(
        f"/plans/{plan['id']}/items/00000000-0000-0000-0000-000000000000", headers=auth_headers
    )
    assert response.status_code == 404


# ---------- InterviewPal practice pack pairing (migration 0004) ----------

PACK = "system-design-week-1"


def test_plan_without_a_pairing_has_none(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    assert plan["interviewpal_pack_key"] is None
    assert client.get(f"/plans/{plan['id']}", headers=auth_headers).json()["interviewpal_pack_key"] is None
    assert client.get("/plans", headers=auth_headers).json()[0]["interviewpal_pack_key"] is None


def test_create_plan_with_a_supported_pack_key(client, auth_headers):
    response = create_plan(client, auth_headers, interviewpal_pack_key=PACK)
    assert response.status_code == 201
    assert response.json()["interviewpal_pack_key"] == PACK
    # survives a reload (a fresh GET)
    assert client.get(f"/plans/{response.json()['id']}", headers=auth_headers).json()["interviewpal_pack_key"] == PACK


@pytest.mark.parametrize("bad", ["not-a-pack", "", "System Design — Week 1", "SYSTEM-DESIGN-WEEK-1", "system-design-week-1 ", 7, ["system-design-week-1"]])
def test_create_plan_rejects_unsupported_pack_keys(client, auth_headers, bad):
    response = create_plan(client, auth_headers, interviewpal_pack_key=bad)
    assert response.status_code == 422
    assert client.get("/plans", headers=auth_headers).json() == []  # nothing was created


def test_update_can_set_a_supported_pack_key(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": PACK}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["interviewpal_pack_key"] == PACK
    assert response.json()["name"] == "4-Week Prep"  # nothing else changed


def test_update_that_omits_the_field_keeps_the_pairing(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_key=PACK).json()
    for body in ({"name": "Renamed"}, {"description": "New text"}, {}):
        response = client.patch(f"/plans/{plan['id']}", json=body, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["interviewpal_pack_key"] == PACK, body


def test_explicit_null_clears_the_pairing(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_key=PACK).json()
    response = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": None}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["interviewpal_pack_key"] is None
    assert client.get(f"/plans/{plan['id']}", headers=auth_headers).json()["interviewpal_pack_key"] is None
    # clearing, then renaming, leaves it cleared
    again = client.patch(f"/plans/{plan['id']}", json={"name": "Still unpaired"}, headers=auth_headers)
    assert again.json()["interviewpal_pack_key"] is None


def test_update_rejects_an_unsupported_key_and_changes_nothing(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_key=PACK).json()
    response = client.patch(f"/plans/{plan['id']}", json={"name": "X", "interviewpal_pack_key": "nope"}, headers=auth_headers)
    assert response.status_code == 422
    saved = client.get(f"/plans/{plan['id']}", headers=auth_headers).json()
    assert saved["interviewpal_pack_key"] == PACK and saved["name"] == "4-Week Prep"


def test_the_same_pack_can_be_paired_with_several_plans(client, auth_headers):
    first = create_plan(client, auth_headers, name="Week 1").json()
    second = create_plan(client, auth_headers, name="Week 1 (copy)").json()
    for plan in (first, second):
        response = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": PACK}, headers=auth_headers)
        assert response.json()["interviewpal_pack_key"] == PACK
    keys = {p["id"]: p["interviewpal_pack_key"] for p in client.get("/plans", headers=auth_headers).json()}
    assert keys == {first["id"]: PACK, second["id"]: PACK}


def test_another_user_cannot_read_or_change_a_pairing(client, auth_headers, other_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_key=PACK).json()
    assert client.get(f"/plans/{plan['id']}", headers=other_headers).status_code == 404
    assert client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": None}, headers=other_headers).status_code == 404
    assert client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": PACK}, headers=other_headers).status_code == 404
    assert client.get(f"/plans/{plan['id']}", headers=auth_headers).json()["interviewpal_pack_key"] == PACK
    assert client.get("/plans", headers=other_headers).json() == []


def test_pairing_requires_a_token(client):
    assert client.post("/plans", json={"name": "x", "interviewpal_pack_key": PACK}).status_code == 401


# ---------- Several packs per plan (migration 0005): the list form ----------

HASHING = "system-design-consistent-hashing"
CAP = "system-design-cap-consistency"


def test_a_plan_with_no_pairing_has_an_empty_list(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    assert plan["interviewpal_pack_keys"] == []
    assert plan["interviewpal_pack_key"] is None


def test_create_with_several_packs_keeps_their_order(client, auth_headers):
    response = create_plan(client, auth_headers, interviewpal_pack_keys=[CAP, HASHING, PACK])
    assert response.status_code == 201
    body = response.json()
    assert body["interviewpal_pack_keys"] == [CAP, HASHING, PACK]
    assert body["interviewpal_pack_key"] == CAP  # the deprecated alias is the first
    assert client.get(f"/plans/{body['id']}", headers=auth_headers).json()["interviewpal_pack_keys"] == [CAP, HASHING, PACK]


@pytest.mark.parametrize("bad", [["nope"], [HASHING, "nope"], [HASHING, HASHING], [""], "system-design-week-1", [7], [[HASHING]]])
def test_unsupported_or_repeated_pack_lists_are_rejected(client, auth_headers, bad):
    assert create_plan(client, auth_headers, interviewpal_pack_keys=bad).status_code == 422
    assert client.get("/plans", headers=auth_headers).json() == []


def test_update_with_a_list_sets_it_and_omitting_keeps_it(client, auth_headers):
    plan = create_plan(client, auth_headers).json()
    response = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": [HASHING, CAP]}, headers=auth_headers)
    assert response.json()["interviewpal_pack_keys"] == [HASHING, CAP]
    for body in ({"name": "Renamed"}, {"description": "x"}, {}):
        kept = client.patch(f"/plans/{plan['id']}", json=body, headers=auth_headers)
        assert kept.json()["interviewpal_pack_keys"] == [HASHING, CAP], body


def test_an_explicit_empty_list_or_null_clears_the_pairing(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_keys=[HASHING, CAP]).json()
    cleared = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": []}, headers=auth_headers).json()
    assert cleared["interviewpal_pack_keys"] == [] and cleared["interviewpal_pack_key"] is None
    again = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": [CAP]}, headers=auth_headers).json()
    assert again["interviewpal_pack_keys"] == [CAP]
    nulled = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": None}, headers=auth_headers).json()
    assert nulled["interviewpal_pack_keys"] == []


def test_a_bad_list_on_update_is_rejected_and_changes_nothing(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_keys=[HASHING]).json()
    for bad in (["nope"], [HASHING, HASHING]):
        response = client.patch(f"/plans/{plan['id']}", json={"name": "X", "interviewpal_pack_keys": bad}, headers=auth_headers)
        assert response.status_code == 422
    saved = client.get(f"/plans/{plan['id']}", headers=auth_headers).json()
    assert saved["interviewpal_pack_keys"] == [HASHING] and saved["name"] == "4-Week Prep"


def test_the_old_single_key_form_still_works_as_a_list_of_one(client, auth_headers):
    plan = create_plan(client, auth_headers, interviewpal_pack_key=HASHING).json()
    assert plan["interviewpal_pack_keys"] == [HASHING]
    set_one = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": CAP}, headers=auth_headers).json()
    assert set_one["interviewpal_pack_keys"] == [CAP]
    cleared = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": None}, headers=auth_headers).json()
    assert cleared["interviewpal_pack_keys"] == []
    # the list wins when both are sent
    both = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": [HASHING], "interviewpal_pack_key": CAP}, headers=auth_headers).json()
    assert both["interviewpal_pack_keys"] == [HASHING]


def test_the_same_pack_list_can_belong_to_several_plans_and_only_the_owner_sees_it(client, auth_headers, other_headers):
    first = create_plan(client, auth_headers, name="Week 1", interviewpal_pack_keys=[HASHING, CAP]).json()
    second = create_plan(client, auth_headers, name="Week 1 again", interviewpal_pack_keys=[HASHING]).json()
    keys = {p["id"]: p["interviewpal_pack_keys"] for p in client.get("/plans", headers=auth_headers).json()}
    assert keys == {first["id"]: [HASHING, CAP], second["id"]: [HASHING]}
    assert client.get(f"/plans/{first['id']}", headers=other_headers).status_code == 404
    assert client.patch(f"/plans/{first['id']}", json={"interviewpal_pack_keys": []}, headers=other_headers).status_code == 404
    assert client.get(f"/plans/{first['id']}", headers=auth_headers).json()["interviewpal_pack_keys"] == [HASHING, CAP]


def test_the_deprecated_single_key_column_stays_equal_to_the_first_pack(client, auth_headers, db_session):
    """Migration 0005 keeps the old column so the previous release still works against this schema (code rollback is safe)."""
    from sqlalchemy import text

    def stored(plan_id):
        row = db_session.execute(
            text("SELECT interviewpal_pack_key, interviewpal_pack_keys FROM items.learning_plans WHERE id = :id"), {"id": plan_id}
        ).one()
        return row[0], row[1]

    plan = create_plan(client, auth_headers, interviewpal_pack_keys=[CAP, HASHING]).json()
    assert stored(plan["id"]) == (CAP, [CAP, HASHING])
    client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": [HASHING]}, headers=auth_headers)
    assert stored(plan["id"]) == (HASHING, [HASHING])
    client.patch(f"/plans/{plan['id']}", json={"name": "renamed"}, headers=auth_headers)  # omitted: unchanged
    assert stored(plan["id"]) == (HASHING, [HASHING])
    client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_key": None}, headers=auth_headers)  # the deprecated form clears both
    assert stored(plan["id"]) == (None, [])
    client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": []}, headers=auth_headers)
    assert stored(plan["id"]) == (None, [])


def test_a_plan_last_written_by_the_release_before_0005_still_shows_its_pack(client, auth_headers, db_session):
    """After a code rollback the older release writes only the single-key column; rolling forward again must not lose it."""
    from sqlalchemy import text

    plan = create_plan(client, auth_headers).json()
    db_session.execute(
        text("UPDATE items.learning_plans SET interviewpal_pack_key = :k, interviewpal_pack_keys = '[]'::jsonb WHERE id = :id"),
        {"k": PACK, "id": plan["id"]},
    )
    db_session.expire_all()
    seen = client.get(f"/plans/{plan['id']}", headers=auth_headers).json()
    assert seen["interviewpal_pack_keys"] == [PACK] and seen["interviewpal_pack_key"] == PACK
    # an explicit clear still clears (both columns), and a list write replaces it
    cleared = client.patch(f"/plans/{plan['id']}", json={"interviewpal_pack_keys": []}, headers=auth_headers).json()
    assert cleared["interviewpal_pack_keys"] == []
