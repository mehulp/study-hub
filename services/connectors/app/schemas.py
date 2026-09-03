import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Twitter isn't a valid choice yet — its OAuth flow doesn't exist (Decision
# #3 deferred it), and this connector type only ever gets a push_token
# (Decision #42), not the oauth_* columns Twitter would eventually use.
ConnectionType = Literal["browser_chrome", "browser_firefox"]


class CreateConnectionRequest(BaseModel):
    type: ConnectionType


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    type: ConnectionType
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateConnectionResponse(ConnectionResponse):
    # The only time this is ever visible unhashed (Decision #42) — same
    # pattern as refresh/invite tokens and client secrets.
    push_token: str


class SyncBookmarkItem(BaseModel):
    external_id: str
    title: str
    url: str
    folder_path: str | None = None
    favicon_url: str | None = None
    preview_text: str | None = None
    preview_media_url: str | None = None
    saved_at: datetime


class SyncRequest(BaseModel):
    items: list[SyncBookmarkItem]


class SyncItemResult(BaseModel):
    external_id: str
    status: Literal["created", "already_exists", "error"]
    detail: str | None = None


class SyncResponse(BaseModel):
    results: list[SyncItemResult]
