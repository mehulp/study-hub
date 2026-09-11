import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import IngestAuth, get_current_user_id, get_ingest_auth, load_public_key
from app.db import get_db
from app.models import Item, ItemTag
from app.schemas import ItemIngestRequest, ItemResponse, ItemUpdateRequest, Source


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_public_key()
    yield


app = FastAPI(title="Items Service", lifespan=lifespan)


def _normalize_tags(tags: list[str]) -> list[str]:
    # Lowercased before every write (Decision #62, same pattern as
    # auth.users.email — Decision #17). Deduplicated after lowercasing,
    # since the composite primary key (item_id, tag) would otherwise reject
    # e.g. ["System Design", "system design"] as a literal duplicate insert.
    # dict.fromkeys preserves first-seen order while deduping.
    seen = dict.fromkeys(t.strip().lower() for t in tags if t.strip())
    return list(seen)


@app.post("/")
def ingest(
    payload: ItemIngestRequest,
    auth: IngestAuth = Depends(get_ingest_auth),
    db: Session = Depends(get_db),
) -> JSONResponse:
    if auth.is_service:
        # A service token carries no user identity (Decision #41) — the
        # caller must say who this item belongs to.
        if payload.owner_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="owner_user_id is required when authenticating as a service",
            )
        owner_user_id = payload.owner_user_id
    else:
        # A user token always ingests for itself — payload.owner_user_id,
        # if somehow present, is ignored rather than trusted, so a user
        # token can never be used to write into someone else's items.
        owner_user_id = auth.user_id

    item = Item(
        owner_user_id=owner_user_id,
        source=payload.source,
        external_id=payload.external_id,
        title=payload.title,
        url=payload.url,
        folder_path=payload.folder_path,
        preview_text=payload.preview_text,
        preview_media_url=payload.preview_media_url,
        favicon_url=payload.favicon_url,
        notes=payload.notes,
        saved_at=payload.saved_at,
    )
    item.tags = [ItemTag(tag=t) for t in _normalize_tags(payload.tags)]
    db.add(item)

    try:
        db.commit()
    except IntegrityError:
        # Already ingested — idempotent success, not an error (Decision
        # #33). A connector re-syncing and re-encountering a known bookmark
        # is expected, routine behavior.
        db.rollback()
        existing = (
            db.query(Item)
            .filter(
                Item.owner_user_id == owner_user_id,
                Item.source == payload.source,
                Item.external_id == payload.external_id,
            )
            .first()
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(ItemResponse.model_validate(existing)),
        )

    db.refresh(item)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(ItemResponse.model_validate(item)),
    )


@app.get("/", response_model=list[ItemResponse])
def list_items(
    source: Source | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[Item]:
    query = db.query(Item).filter(Item.owner_user_id == user_id)
    if source is not None:
        query = query.filter(Item.source == source)
    return query.order_by(Item.saved_at.desc()).all()


@app.get("/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Item:
    # owner_user_id is part of the WHERE clause itself, not a check applied
    # after fetching — a request for another user's item returns the same
    # 404 as a nonexistent one, never revealing that the item exists at all
    # (same anti-enumeration reasoning as /login's generic error message).
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.owner_user_id == user_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@app.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Item:
    # Same owner-scoped lookup + anti-enumeration 404 as get_item — a
    # PATCH for another user's item is indistinguishable from a PATCH for a
    # nonexistent one.
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.owner_user_id == user_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # `model_fields_set`, not "is this field None" — a field genuinely
    # absent from the request body is left untouched; a field explicitly
    # sent (including as null) is applied. This is what lets {"notes":
    # null} really clear notes instead of being indistinguishable from not
    # mentioning notes at all (Decision #64).
    fields = payload.model_fields_set
    if "title" in fields:
        if payload.title is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="title cannot be null")
        item.title = payload.title
    if "url" in fields:
        if payload.url is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="url cannot be null")
        item.url = payload.url
    if "notes" in fields:
        item.notes = payload.notes
    if "preview_media_url" in fields:
        item.preview_media_url = payload.preview_media_url
    if "tags" in fields:
        # Reassigning the collection triggers delete-orphan on whatever
        # tags this drops and inserts fresh rows for the rest — SQLAlchemy
        # diffs old vs. new, it isn't a blind delete-all-then-reinsert.
        item.tags = [ItemTag(tag=t) for t in _normalize_tags(payload.tags or [])]

    db.commit()
    db.refresh(item)
    return item


@app.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.owner_user_id == user_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    # ON DELETE CASCADE (migration 0002) handles item_tags — no separate
    # cleanup needed here.
    db.delete(item)
    db.commit()
