import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import bearer_scheme, get_current_user_id, load_public_key
from app.db import get_db
from app.items_client import ItemsServiceError, ingest_item
from app.models import Connection
from app.schemas import (
    ConnectionResponse,
    CreateConnectionRequest,
    CreateConnectionResponse,
    SyncRequest,
    SyncResponse,
)
from app.security import generate_push_token, hash_push_token, verify_push_token

# A real, long-used browser can easily have hundreds of bookmarks. Processing
# them one at a time — each a full network round trip to Items — made a
# large sync take long enough to blow past Gateway's own upstream timeout,
# which had no error handling and let the failure leak through as a raw
# 500 page. Bounded concurrency fixes the root cause (slow batches), not
# just the symptom; the bound itself avoids opening an unbounded number of
# simultaneous connections to Items/Postgres for a very large collection.
SYNC_CONCURRENCY_LIMIT = 10

# Items only knows about the normalized source, not the connection-type
# label Connectors/the schema use — "browser_chrome" is a distinct value
# from "browser_firefox" here because it also gates a Connection's own
# type-specific columns (Decision #42's schema note), but Items just wants
# "chrome"/"firefox" like every other item.
CONNECTION_TYPE_TO_SOURCE = {
    "browser_chrome": "chrome",
    "browser_firefox": "firefox",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_public_key()
    yield


app = FastAPI(title="Connectors Service", lifespan=lifespan)


@app.post("/connections", response_model=CreateConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_connection(
    payload: CreateConnectionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CreateConnectionResponse:
    push_token = generate_push_token()
    connection = Connection(
        owner_user_id=user_id,
        type=payload.type,
        push_token_hash=hash_push_token(push_token),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)

    return CreateConnectionResponse(
        id=connection.id,
        type=connection.type,
        last_synced_at=connection.last_synced_at,
        created_at=connection.created_at,
        push_token=push_token,  # only ever visible here, unhashed (Decision #42)
    )


@app.get("/connections", response_model=list[ConnectionResponse])
def list_connections(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Connection]:
    return db.query(Connection).filter(Connection.owner_user_id == user_id).all()


def get_connection_by_push_token(
    connection_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Connection:
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    # Wrong id, or a connection with no push_token_hash (a Twitter
    # connection, which doesn't use this auth path at all), or a
    # non-matching token — same 404 in every case, so a sync attempt never
    # reveals whether a given connection id exists (same anti-enumeration
    # reasoning used throughout the rest of the project).
    if (
        connection is None
        or connection.push_token_hash is None
        or not verify_push_token(credentials.credentials, connection.push_token_hash)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return connection


async def _sync_one(semaphore: asyncio.Semaphore, owner_user_id: uuid.UUID, source: str, bookmark) -> dict:
    item_payload = {
        "source": source,
        "external_id": bookmark.external_id,
        "title": bookmark.title,
        "url": bookmark.url,
        "folder_path": bookmark.folder_path,
        "favicon_url": bookmark.favicon_url,
        "preview_text": bookmark.preview_text,
        "preview_media_url": bookmark.preview_media_url,
        "saved_at": bookmark.saved_at.isoformat(),
    }
    async with semaphore:
        try:
            status_code, _ = await ingest_item(owner_user_id, item_payload)
        except ItemsServiceError as exc:
            # One failure never blocks the rest of the batch (Decision #44).
            return {"external_id": bookmark.external_id, "status": "error", "detail": str(exc)}

    item_status = "created" if status_code == 201 else "already_exists"
    return {"external_id": bookmark.external_id, "status": item_status}


@app.post("/connections/{connection_id}/sync", response_model=SyncResponse)
async def sync_connection(
    connection_id: uuid.UUID,
    payload: SyncRequest,
    connection: Connection = Depends(get_connection_by_push_token),
    db: Session = Depends(get_db),
) -> SyncResponse:
    source = CONNECTION_TYPE_TO_SOURCE[connection.type]
    semaphore = asyncio.Semaphore(SYNC_CONCURRENCY_LIMIT)

    results = await asyncio.gather(
        *(_sync_one(semaphore, connection.owner_user_id, source, bookmark) for bookmark in payload.items)
    )

    connection.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return SyncResponse(results=results)
