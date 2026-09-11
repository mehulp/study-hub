import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class CreateBoardRequest(BaseModel):
    name: str


class BoardResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    owner_email: str | None
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
    owner_email: str | None
    name: str
    created_at: datetime
    role: str
    items: list[BoardItemResponse]


class AccessGrantSummaryResponse(BaseModel):
    invited_email: str
    status: str
    role: str
    created_at: datetime  # invited_at
    accepted_at: datetime | None

    model_config = {"from_attributes": True}


class OwnedBoardResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    item_count: int
    grants: list[AccessGrantSummaryResponse]


class SharedBoardResponse(BaseModel):
    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    owner_email: str | None
    role: str
    accepted_at: datetime
    item_count: int


class InviteRequest(BaseModel):
    invited_email: EmailStr


class InviteResponse(BaseModel):
    board_id: uuid.UUID
    invited_email: str
    role: str
    # The only time this is ever visible unhashed (Decision #36) — whatever
    # hands this to the recipient (manual share, or a future mail
    # integration, Decision #38) has to capture it right here.
    invite_token: str
    expires_at: datetime
