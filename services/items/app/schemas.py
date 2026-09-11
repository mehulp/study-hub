import uuid
from datetime import datetime
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
