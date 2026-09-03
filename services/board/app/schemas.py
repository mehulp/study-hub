import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateBoardRequest(BaseModel):
    name: str


class BoardResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AddItemRequest(BaseModel):
    item_id: uuid.UUID


class BoardItemResponse(BaseModel):
    item_id: uuid.UUID
    title: str
    url: str
    favicon_url: str | None
    preview_text: str | None
    preview_media_url: str | None
    added_at: datetime

    model_config = {"from_attributes": True}


class BoardWithItemsResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    created_at: datetime
    role: str
    items: list[BoardItemResponse]
