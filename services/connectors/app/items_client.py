import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]
ITEMS_SERVICE_URL = os.environ["ITEMS_SERVICE_URL"]
OAUTH_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
OAUTH_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]

# Cached in memory and reused across requests until near expiry, rather than
# fetched fresh on every sync call — a client secret is a long-lived
# credential, but there's no reason to pay the round trip to Auth on every
# single item when the token itself is still valid (Decision #41).
_cached_token: str | None = None
_cached_token_expires_at: datetime | None = None


class ItemsServiceError(Exception):
    """Items (or Auth's token endpoint) was unreachable, timed out, or
    returned an error — a real upstream failure for this one item, not
    "item already exists" or any other normal outcome."""


async def _get_service_token() -> str:
    global _cached_token, _cached_token_expires_at
    now = datetime.now(timezone.utc)
    if (
        _cached_token is not None
        and _cached_token_expires_at is not None
        and _cached_token_expires_at > now + timedelta(seconds=30)
    ):
        return _cached_token

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/oauth/token",
                json={"client_id": OAUTH_CLIENT_ID, "client_secret": OAUTH_CLIENT_SECRET},
                timeout=5.0,
            )
    except httpx.HTTPError as exc:
        raise ItemsServiceError(f"Auth token request failed: {exc}") from exc

    if response.status_code != 200:
        raise ItemsServiceError(f"Auth token request returned {response.status_code}")

    body = response.json()
    _cached_token = body["access_token"]
    _cached_token_expires_at = now + timedelta(seconds=body["expires_in"])
    return _cached_token


async def ingest_item(owner_user_id: uuid.UUID, item: dict) -> tuple[int, dict]:
    """Calls Items' ingest with a service token on this connection owner's
    behalf. Returns (status_code, body) — 201 for a genuinely new item, 200
    for one Items already had (Decision #33's idempotency); the caller
    needs that distinction to report "created" vs "already_exists"
    per-item, not just "it worked." Raises ItemsServiceError for anything
    else, including a stale-token 401 (cache cleared so the next call
    re-authenticates rather than repeating the same failure)."""
    token = await _get_service_token()
    payload = {**item, "owner_user_id": str(owner_user_id)}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ITEMS_SERVICE_URL}/",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )
    except httpx.HTTPError as exc:
        raise ItemsServiceError(f"Items request failed: {exc}") from exc

    if response.status_code in (200, 201):
        return response.status_code, response.json()

    if response.status_code == 401:
        global _cached_token
        _cached_token = None

    raise ItemsServiceError(f"Items returned {response.status_code}: {response.text}")
