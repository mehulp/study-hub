"""Seeds the Study Hub demo: two accounts, ~70 curated system-design study
resources for the owner, and a shared board the receiver accepts.

Reads scripts/system_design_resources.csv (curated from a personal Excel
checklist — see docs/study-hub-architecture.md Decision #67) and calls the
real API through Gateway, exactly like the web UI would. Not idempotent:
re-running against a database that already has this data will hit Items'
existing-URL uniqueness constraint and mostly no-op (safe), but accounts
that already exist will fail signup (also handled, see signup_and_login).

Usage: ./venv/bin/python scripts/seed_demo_data.py
Requires: the full Docker stack up (docker compose up -d), the `requests`
library (pip install requests — not in any service's requirements.txt,
since only this one-off script needs it).
"""
import csv
import os
import re
import secrets
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

GATEWAY = os.environ.get("GATEWAY_URL", "http://localhost:8000")
CSV_PATH = Path(__file__).parent / "system_design_resources.csv"

OWNER_EMAIL = "mehulpatankar_owner@gmail.com"
RECEIVER_EMAIL = "mehulpatankar_receiver@gmail.com"
BOARD_NAME = "System Design Fundamentals"

SOURCE_TAG = {
    "ByteByteGo": "bytebytego", "ByteByteGo 2": "bytebytego", "ByteByteGo 3": "bytebytego", "ByteByteGo 4": "bytebytego",
    "Hello Interview": "hellointerview", "Hello Interview 2": "hellointerview",
    "Hello Interview YouTube": "video", "Hello Interview YouTube 2": "video",
}
CORE_COMPONENT_TOPICS = {
    "Key Technologies overview", "Database: PostgreSQL", "Database: DynamoDB", "Cache: Redis",
    "Message Queue: Kafka", "Load Balancer / API Gateway", "Blob Storage & CDN",
}
TOPIC_TAGS = {
    "What is a System Design Interview?": ["interview-basics"],
    "Delivery framework (how to structure any answer)": ["interview-framework"],
    "Networking & API design": ["networking", "api-design"],
    "Data modeling": ["data-modeling"],
    "Choosing & indexing databases": ["databases", "indexing"],
    "Caching": ["caching"],
    "Sharding & Consistent Hashing": ["sharding", "consistent-hashing"],
    "CAP theorem & consistency trade-offs": ["cap-theorem", "consistency"],
    "Async & messaging (queues)": ["messaging", "kafka"],
    "Reliability / fault tolerance / high availability": ["reliability", "high-availability"],
    "Numbers to know (latency/throughput intuition)": ["capacity-estimation"],
    "Identity / IAM-specific": ["iam", "authentication", "authorization"],
    "Key Technologies overview": [],
    "Database: PostgreSQL": ["databases", "postgresql"],
    "Database: DynamoDB": ["databases", "dynamodb"],
    "Cache: Redis": ["caching", "redis"],
    "Message Queue: Kafka": ["messaging", "kafka"],
    "Load Balancer / API Gateway": ["load-balancing", "api-gateway"],
    "Blob Storage & CDN": ["blob-storage", "cdn"],
    "How DBs work indetail": ["databases", "deep-dive"],
    "Design a URL shortener / rate limiter": ["url-shortener", "rate-limiter"],
    "Design a notification system": ["notifications"],
    "Ticketmaster": ["concurrency", "ticketing"],
    "Dropbox": ["file-storage", "sync"],
    "Ad Click Aggregator": ["analytics", "event-processing"],
    "Web Crawler": ["distributed-scheduling", "web-crawler"],
    "FB Post Search": ["search", "indexing"],
    "WhatsApp": ["messaging", "real-time"],
    "LeetCode": ["code-execution", "sandboxing"],
    "Uber": ["geospatial", "matching"],
    "FB News Feed": ["ranking", "personalization"],
}
ACRONYMS = {"cap", "api", "cdn", "sso", "jwt", "rbac", "abac", "iam", "sql", "nosql",
            "crud", "http", "https", "tcp", "l4", "l7", "oauth2", "oauth", "oidc", "ttl", "lru", "s3", "db", "dbs", "fb"}
# Product names that need specific internal casing an acronym-style
# upper() would get wrong (e.g. "dynamodb".upper() -> "DYNAMODB", not
# "DynamoDB"). Keyed by the lowercased single-word slug.
PRODUCT_NAMES = {"dynamodb": "DynamoDB", "leetcode": "LeetCode", "whatsapp": "WhatsApp"}

# Two kinds of known exceptions to the general derivation rules below, found
# by comparing a first seeding pass against the live result (see Decision
# #67): (a) two different URLs under one topic both fall back to the same
# generic "{topic} -- Video Walkthrough" title since videos have no usable
# URL slug: b) two different *sources* happen to use the identical URL
# slug ("consistent-hashing" on both bytebytego.com and hellointerview.com).
# Both are genuine collisions the general rules can't resolve on their own,
# not the common case -- keyed by URL, applied after the general rules.
TITLE_OVERRIDES = {
    "https://www.youtube.com/watch?v=DU8o-OTeoCc": "Kafka — Video Walkthrough",
    "https://www.youtube.com/watch?v=L521gizea4s": "Sharding — Video Walkthrough",
    "https://www.youtube.com/watch?v=vccwdhfqIrI": "Consistent Hashing — Video Walkthrough",
    "https://bytebytego.com/guides/consistent-hashing": "Consistent Hashing (ByteByteGo)",
    "https://www.hellointerview.com/learn/system-design/core-concepts/consistent-hashing": "Consistent Hashing (Hello Interview)",
    "https://www.youtube.com/watch?v=SHkbPm1Wrno": "Networking — Video Walkthrough",
    "https://www.youtube.com/watch?v=DQ57zYedMdQ": "API Design — Video Walkthrough",
}


def title_from_slug(url: str) -> str:
    slug = url.rstrip("/").split("/")[-1]
    words = re.split(r"[-_]", slug)
    if len(words) == 1 and words[0].lower() in PRODUCT_NAMES:
        return PRODUCT_NAMES[words[0].lower()]
    return " ".join(w.upper() if w.lower() in ACRONYMS else w.capitalize() for w in words)


def build_title(topic: str, url: str) -> str:
    if url in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[url]
    if "youtube.com" in url:
        return f"{topic} — Video Walkthrough"
    if "excalidraw.com" in url:
        return f"{topic} — Diagram"
    return title_from_slug(url)


def build_tags(section_label: str, topic: str, source: str) -> list[str]:
    tags = ["system-design"]
    if section_label == "Structured Learning Path":
        tags.append("core-components" if topic in CORE_COMPONENT_TOPICS else "fundamentals")
    else:
        tags.append({"Likely Questions": "likely-questions", "Practice Problems": "practice-problems"}[section_label])
    tags.extend(TOPIC_TAGS.get(topic, []))
    tags.append(SOURCE_TAG[source])
    return list(dict.fromkeys(tags))  # de-dupe, preserve order


def load_resources() -> list[dict]:
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Merge rows that share a URL (the same resource genuinely referenced by
    # more than one topic, e.g. the Kafka deep-dive from both "Async &
    # messaging" and "Message Queue: Kafka") -- union their tags rather than
    # letting whichever topic's POST happens to run first silently win and
    # the other's tags get dropped by Items' idempotent-ingest behavior
    # (Decision #33).
    by_url = defaultdict(list)
    for row in rows:
        by_url[row["url"]].append(row)

    resources = []
    for url, group in by_url.items():
        primary = group[0]
        tags: list[str] = []
        for row in group:
            tags.extend(build_tags(row["section_label"], row["topic"], row["source"]))
        resources.append({
            "url": url,
            "title": build_title(primary["topic"], url),
            "notes": primary["notes"],
            "tags": list(dict.fromkeys(tags)),
            "in_fundamentals": any(r["section_label"] == "Structured Learning Path" for r in group),
        })
    return resources


def signup_and_login(email: str, password: str, first_name: str | None = None) -> str:
    payload = {"email": email, "password": password}
    if first_name:
        payload["first_name"] = first_name
    r = requests.post(f"{GATEWAY}/auth/signup", json=payload)
    if r.status_code not in (201, 409):
        print(f"signup {email}: {r.status_code} {r.text}")
    r = requests.post(f"{GATEWAY}/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> None:
    # Overridable so this can be re-run against a target where the owner
    # account already exists (e.g. deployed, signed up through the UI
    # first) -- signup_and_login already tolerates a 409, it just needs
    # the real password to log in with instead of a fresh random one.
    owner_password = os.environ.get("OWNER_PASSWORD") or secrets.token_urlsafe(16)
    receiver_password = os.environ.get("RECEIVER_PASSWORD") or secrets.token_urlsafe(16)

    resources = load_resources()
    print(f"Loaded {len(resources)} distinct resources from {CSV_PATH.name}")

    owner_token = signup_and_login(OWNER_EMAIL, owner_password, first_name="Mehul")
    receiver_token = signup_and_login(RECEIVER_EMAIL, receiver_password, first_name="Study Partner")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    created_ids, fundamentals_ids = [], []
    for res in resources:
        payload = {
            "source": "manual", "external_id": res["url"], "title": res["title"],
            "url": res["url"], "notes": res["notes"], "tags": res["tags"],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        r = requests.post(f"{GATEWAY}/items", json=payload, headers=owner_headers)
        if r.status_code not in (200, 201):
            print(f"FAILED item: {res['title']} -> {r.status_code} {r.text}")
            continue
        item_id = r.json()["id"]
        created_ids.append(item_id)
        if res["in_fundamentals"]:
            fundamentals_ids.append(item_id)
    print(f"Created {len(created_ids)}/{len(resources)} items for owner")

    r = requests.post(f"{GATEWAY}/board", json={"name": BOARD_NAME}, headers=owner_headers)
    r.raise_for_status()
    board_id = r.json()["id"]
    for item_id in fundamentals_ids:
        requests.post(f"{GATEWAY}/board/{board_id}/items", json={"item_id": item_id}, headers=owner_headers)
    print(f"Board {board_id!r} created with {len(fundamentals_ids)} items")

    r = requests.post(f"{GATEWAY}/board/{board_id}/invite", json={"invited_email": RECEIVER_EMAIL}, headers=owner_headers)
    r.raise_for_status()
    invite_token = r.json()["invite_token"]

    r = requests.post(f"{GATEWAY}/board/invites/{invite_token}/accept", headers={"Authorization": f"Bearer {receiver_token}"})
    r.raise_for_status()
    print(f"Receiver accepted: role={r.json()['role']}, {len(r.json()['items'])} items visible")

    print("\n=== Credentials (save these -- shown once) ===")
    print(f"Owner:    {OWNER_EMAIL} / {owner_password}")
    print(f"Receiver: {RECEIVER_EMAIL} / {receiver_password}")


if __name__ == "__main__":
    main()
