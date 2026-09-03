import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

ITEMS_SERVICE_URL = os.environ["ITEMS_SERVICE_URL"]


class ItemsServiceError(Exception):
    """Items was unreachable, timed out, or returned something other than a
    clean 200/404 — a real upstream problem, not "item not found." Callers
    should surface this distinctly rather than let it crash as a bare 500."""


async def fetch_item(item_id: uuid.UUID, bearer_token: str) -> dict | None:
    """Fetch one item, scoped to whoever the token belongs to — Items
    applies its own ownership check exactly as if the caller had asked
    directly (Decision #30: the forwarded token is real, not trusted
    blindly). Returns None if the item doesn't exist or isn't the caller's.
    Raises ItemsServiceError if Items itself couldn't be reached or failed."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ITEMS_SERVICE_URL}/{item_id}",
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=5.0,
            )
    except httpx.HTTPError as exc:
        raise ItemsServiceError(f"Items request failed: {exc}") from exc

    if response.status_code == 404:
        return None
    if response.status_code >= 400:
        # Includes a 401 — e.g. the caller's token expired in the small
        # window between Board's own check and this outbound call. Not the
        # same as "item not found," so it must not be treated as one.
        raise ItemsServiceError(f"Items returned {response.status_code}")
    return response.json()
