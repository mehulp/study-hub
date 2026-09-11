import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import IngestAuth, get_current_user_id, get_ingest_auth, load_public_key
from app.db import get_db
from app.models import Item, ItemTag, LearningPlan, PlanItem
from app.schemas import (
    ItemIngestRequest,
    ItemResponse,
    ItemUpdateRequest,
    PlanCreateRequest,
    PlanItemAddRequest,
    PlanItemResponse,
    PlanItemUpdateRequest,
    PlanResponse,
    PlanUpdateRequest,
    Source,
)


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


def _get_owned_plan(plan_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> LearningPlan:
    # Same owner-in-the-WHERE-clause anti-enumeration pattern as
    # get_item/update_item below — another user's plan looks exactly like a
    # nonexistent one.
    plan = (
        db.query(LearningPlan)
        .filter(LearningPlan.id == plan_id, LearningPlan.owner_user_id == user_id)
        .first()
    )
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def _plan_item_response(plan_item: PlanItem) -> PlanItemResponse:
    return PlanItemResponse(
        plan_id=plan_item.plan_id,
        item_id=plan_item.item_id,
        title=plan_item.item.title,
        url=plan_item.item.url,
        tags=[t.tag for t in plan_item.item.tags],
        status=plan_item.status,
        order_index=plan_item.order_index,
        priority=plan_item.priority,
        target_date=plan_item.target_date,
        estimated_effort_minutes=plan_item.estimated_effort_minutes,
        added_at=plan_item.added_at,
    )


def _plan_response(plan: LearningPlan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        owner_user_id=plan.owner_user_id,
        name=plan.name,
        description=plan.description,
        created_at=plan.created_at,
        items=[_plan_item_response(pi) for pi in plan.items],
    )


# Registered before the generic /{item_id} routes below — a single dynamic
# path segment matches the literal string "plans" too, so /plans would
# otherwise 422 trying to parse "plans" as a UUID rather than ever reaching
# these handlers (same ordering fix Decision #68 already made for Board).
@app.post("/plans", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = LearningPlan(owner_user_id=user_id, name=payload.name, description=payload.description)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _plan_response(plan)


@app.get("/plans", response_model=list[PlanResponse])
def list_plans(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[PlanResponse]:
    plans = (
        db.query(LearningPlan)
        .filter(LearningPlan.owner_user_id == user_id)
        .order_by(LearningPlan.created_at.desc())
        .all()
    )
    return [_plan_response(plan) for plan in plans]


@app.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    return _plan_response(_get_owned_plan(plan_id, user_id, db))


@app.patch("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: uuid.UUID,
    payload: PlanUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = _get_owned_plan(plan_id, user_id, db)
    fields = payload.model_fields_set
    if "name" in fields:
        if payload.name is None or not payload.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name cannot be blank")
        plan.name = payload.name
    if "description" in fields:
        plan.description = payload.description
    db.commit()
    db.refresh(plan)
    return _plan_response(plan)


@app.delete("/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(
    plan_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    plan = _get_owned_plan(plan_id, user_id, db)
    # ON DELETE CASCADE (migration 0003) handles plan_items — no separate
    # cleanup needed here. Does not touch the underlying items themselves.
    db.delete(plan)
    db.commit()


@app.post("/plans/{plan_id}/items", response_model=PlanItemResponse, status_code=status.HTTP_201_CREATED)
def add_plan_item(
    plan_id: uuid.UUID,
    payload: PlanItemAddRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanItemResponse:
    plan = _get_owned_plan(plan_id, user_id, db)
    # The item must also belong to this same user — same owner-scoped
    # lookup as everywhere else, so a plan can never reference an item the
    # caller doesn't actually own.
    item = db.query(Item).filter(Item.id == payload.item_id, Item.owner_user_id == user_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    plan_item = PlanItem(
        plan_id=plan.id,
        item_id=item.id,
        status=payload.status,
        order_index=payload.order_index,
        priority=payload.priority,
        target_date=payload.target_date,
        estimated_effort_minutes=payload.estimated_effort_minutes,
    )
    db.add(plan_item)
    try:
        db.commit()
    except IntegrityError:
        # Composite PK (plan_id, item_id) already exists — same "reject the
        # duplicate cleanly" instinct as Board's duplicate-invite check
        # (Decision #77), not a raw constraint-violation leak.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This item is already on this plan")

    db.refresh(plan_item)
    return _plan_item_response(plan_item)


@app.patch("/plans/{plan_id}/items/{item_id}", response_model=PlanItemResponse)
def update_plan_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PlanItemUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanItemResponse:
    plan = _get_owned_plan(plan_id, user_id, db)
    plan_item = (
        db.query(PlanItem).filter(PlanItem.plan_id == plan.id, PlanItem.item_id == item_id).first()
    )
    if plan_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan item not found")

    fields = payload.model_fields_set
    if "status" in fields:
        if payload.status is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status cannot be null")
        plan_item.status = payload.status
    if "order_index" in fields:
        plan_item.order_index = payload.order_index
    if "priority" in fields:
        plan_item.priority = payload.priority
    if "target_date" in fields:
        plan_item.target_date = payload.target_date
    if "estimated_effort_minutes" in fields:
        plan_item.estimated_effort_minutes = payload.estimated_effort_minutes

    db.commit()
    db.refresh(plan_item)
    return _plan_item_response(plan_item)


@app.delete("/plans/{plan_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_plan_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    plan = _get_owned_plan(plan_id, user_id, db)
    deleted = (
        db.query(PlanItem).filter(PlanItem.plan_id == plan.id, PlanItem.item_id == item_id).delete()
    )
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan item not found")
    db.commit()


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
