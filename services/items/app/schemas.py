import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Source = Literal["twitter", "chrome", "firefox"]


class ItemIngestRequest(BaseModel):
    source: Source
    external_id: str
    title: str
    url: str
    folder_path: str | None = None
    preview_text: str | None = None
    preview_media_url: str | None = None
    favicon_url: str | None = None
    saved_at: datetime


class ItemResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    source: Source
    external_id: str
    title: str
    url: str
    folder_path: str | None
    preview_text: str | None
    preview_media_url: str | None
    favicon_url: str | None
    saved_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
