import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_validator

# "twitter" retired (Decision #63) — no item has ever actually been created
# with it, since tweet-fetching was never built. "manual" added for
# web-UI-entered resources (Decision #60).
Source = Literal["manual", "chrome", "firefox"]


class ItemIngestRequest(BaseModel):
    source: Source
    external_id: str
    title: str
    url: str
    folder_path: str | None = None
    preview_text: str | None = None
    preview_media_url: str | None = None
    favicon_url: str | None = None
    notes: str | None = None
    tags: list[str] = []
    saved_at: datetime
    # Required only for service-authenticated ingest (Decision #41) — a
    # service token carries no user identity to derive this from, unlike a
    # user token, which ignores this field and always uses its own sub.
    owner_user_id: uuid.UUID | None = None


class ItemUpdateRequest(BaseModel):
    """PATCH payload. Standard partial-update semantics: a field omitted
    from the request body is left unchanged; a field explicitly present
    (even as null/empty) is applied as given. The endpoint distinguishes
    the two via `model_fields_set`, not by treating None as "no change" —
    that's what lets `{"notes": null}` genuinely clear notes rather than
    being indistinguishable from not mentioning notes at all."""

    title: str | None = None
    url: str | None = None
    notes: str | None = None
    preview_media_url: str | None = None
    tags: list[str] | None = None


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
    notes: str | None
    tags: list[str]
    saved_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("tags", mode="before")
    @classmethod
    def _tags_as_strings(cls, value: list) -> list[str]:
        # `Item.tags` (from_attributes) is a list of ItemTag ORM objects;
        # application code building a response directly may already pass
        # plain strings. Handle both without needing two schema shapes.
        return [v.tag if hasattr(v, "tag") else v for v in value]


# Learning Plans (roadmap Phase 1, Decision #85).
PlanItemStatus = Literal["not_started", "in_progress", "completed", "skipped"]
Priority = Literal["low", "medium", "high"]


class PlanCreateRequest(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name cannot be blank")
        return trimmed


class PlanUpdateRequest(BaseModel):
    """PATCH payload — same model_fields_set partial-update semantics as
    ItemUpdateRequest (Decision #64)."""

    name: str | None = None
    description: str | None = None


class PlanItemAddRequest(BaseModel):
    item_id: uuid.UUID
    status: PlanItemStatus = "not_started"
    order_index: int | None = None
    priority: Priority | None = None
    target_date: date | None = None
    estimated_effort_minutes: int | None = None


class PlanItemUpdateRequest(BaseModel):
    """PATCH payload for one plan item's own status/order/priority/etc.
    Same model_fields_set partial-update semantics as ItemUpdateRequest."""

    status: PlanItemStatus | None = None
    order_index: int | None = None
    priority: Priority | None = None
    target_date: date | None = None
    estimated_effort_minutes: int | None = None


class PlanItemResponse(BaseModel):
    # title/url/tags are composed live from the item this row references
    # (a real FK, Decision #85) — not a write-time snapshot the way
    # Board's denormalized fields are (Decision #37). Board snapshots
    # because it's a different service and a live cross-service call on
    # every read was the thing being avoided; here, plan_items and items
    # share a schema, so reading the current row is just a join, not a
    # network call — there's nothing to avoid.
    plan_id: uuid.UUID
    item_id: uuid.UUID
    title: str
    url: str
    tags: list[str]
    status: PlanItemStatus
    order_index: int | None
    priority: Priority | None
    target_date: date | None
    estimated_effort_minutes: int | None
    added_at: datetime


class PlanResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    items: list[PlanItemResponse]
