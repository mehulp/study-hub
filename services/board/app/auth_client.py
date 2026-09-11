import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()

AUTH_SERVICE_URL = os.environ["AUTH_SERVICE_URL"]


class AuthServiceError(Exception):
    """Auth was unreachable, timed out, or returned something other than a
    clean 200 — a real upstream problem, not something to swallow silently.
    Same shape as ItemsServiceError in items_client.py."""


@dataclass
class OwnIdentity:
    email: str
    first_name: str | None


async def fetch_own_identity(bearer_token: str) -> OwnIdentity:
    """Resolves the caller's own identity via Auth's /me — never anyone
    else's. A user asking Auth about themselves is a fundamentally
    different, much smaller capability than a general "resolve any user id
    to an identity" lookup would be (Decision #70) — no new authority is
    granted to Board here, just one more thing a normal user token can do
    what it could already do. Returns both email (Decision #71) and
    first_name (Decision #75) from the same /me call — Auth's response
    already carries both since Decision #73, no second round trip."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{AUTH_SERVICE_URL}/me",
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=5.0,
            )
    except httpx.HTTPError as exc:
        raise AuthServiceError(f"Auth request failed: {exc}") from exc

    if response.status_code != 200:
        raise AuthServiceError(f"Auth returned {response.status_code}")
    body = response.json()
    return OwnIdentity(email=body["email"], first_name=body.get("first_name"))
