import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

ITEMS_SERVICE_URL = os.environ["ITEMS_SERVICE_URL"]


async def fetch_item(item_id: uuid.UUID, bearer_token: str) -> dict | None:
    """Fetch one item, scoped to whoever the token belongs to — Items
    applies its own ownership check exactly as if the caller had asked
    directly (Decision #30: the forwarded token is real, not trusted
    blindly). Returns None if the item doesn't exist or isn't the caller's."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ITEMS_SERVICE_URL}/{item_id}",
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=5.0,
        )

    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()
