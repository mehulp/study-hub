import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user_id, get_current_user_id_and_token, load_public_key
from app.auth_client import fetch_own_identity, AuthServiceError
from app.db import get_db
from app.items_client import fetch_item, ItemsServiceError
from app.models import AccessGrant, Board, BoardItem
from app.schemas import (
    AccessGrantSummaryResponse,
    AddItemRequest,
    BoardItemResponse,
    BoardResponse,
    BoardWithItemsResponse,
    CreateBoardRequest,
    InviteRequest,
    InviteResponse,
    OwnedBoardResponse,
    SharedBoardResponse,
)
from app.security import generate_invite_token, hash_invite_token, INVITE_TOKEN_TTL


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_public_key()
    yield


app = FastAPI(title="Board Service", lifespan=lifespan)


def _resolve_role(board: Board, user_id: uuid.UUID, db: Session) -> str | None:
    """'owner', an accepted grant's role ('viewer'/'editor'), or None if the
    user has no access to this board at all."""
    if board.owner_user_id == user_id:
        return "owner"

    grant = (
        db.query(AccessGrant)
        .filter(
            AccessGrant.board_id == board.id,
            AccessGrant.user_id == user_id,
            AccessGrant.status == "accepted",
        )
        .first()
    )
    return grant.role if grant else None


def _get_board_with_role(board_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> tuple[Board, str]:
    board = db.query(Board).filter(Board.id == board_id).first()
    # Board doesn't exist, or exists but this user has no access to it —
    # same 404 either way, so a board's existence is never revealed to
    # someone who isn't on it in some role (same anti-enumeration reasoning
    # as Items' get_item).
    role = _resolve_role(board, user_id, db) if board is not None else None
    if board is None or role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return board, role


@app.post("/", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
async def create_board(
    payload: CreateBoardRequest,
    auth: tuple[uuid.UUID, str] = Depends(get_current_user_id_and_token),
    db: Session = Depends(get_db),
) -> Board:
    user_id, token = auth
    # Denormalized at creation time (Decision #70, extended by #75 to also
    # capture first_name) — a user asking Auth about themselves, not a new
    # "resolve anyone's identity" capability.
    try:
        identity = await fetch_own_identity(token)
    except AuthServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service is unavailable — try again shortly",
        )

    board = Board(
        owner_user_id=user_id,
        owner_email=identity.email,
        owner_first_name=identity.first_name,
        name=payload.name,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def _board_with_items_response(board: Board, role: str, db: Session) -> BoardWithItemsResponse:
    items = (
        db.query(BoardItem)
        .filter(BoardItem.board_id == board.id)
        .order_by(BoardItem.added_at.desc())
        .all()
    )
    return BoardWithItemsResponse(
        id=board.id,
        owner_user_id=board.owner_user_id,
        owner_email=board.owner_email,
        owner_first_name=board.owner_first_name,
        name=board.name,
        created_at=board.created_at,
        role=role,
        items=[BoardItemResponse.model_validate(i) for i in items],
    )


# Registered before GET /{board_id}: FastAPI/Starlette matches routes in
# registration order, and /{board_id} is typed as uuid.UUID — if it came
# first, a request for /mine would structurally match that single-segment
# pattern before ever reaching this literal route, then fail UUID coercion
# on the string "mine" and 422 instead of hitting this handler at all.
@app.get("/mine", response_model=list[OwnedBoardResponse])
def list_my_boards(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[OwnedBoardResponse]:
    boards = (
        db.query(Board)
        .filter(Board.owner_user_id == user_id)
        .order_by(Board.created_at.desc())
        .all()
    )
    result = []
    for board in boards:
        item_count = db.query(BoardItem).filter(BoardItem.board_id == board.id).count()
        grants = (
            db.query(AccessGrant)
            .filter(AccessGrant.board_id == board.id)
            .order_by(AccessGrant.created_at.asc())
            .all()
        )
        result.append(
            OwnedBoardResponse(
                id=board.id,
                name=board.name,
                created_at=board.created_at,
                item_count=item_count,
                grants=[AccessGrantSummaryResponse.model_validate(g) for g in grants],
            )
        )
    return result


@app.get("/shared-with-me", response_model=list[SharedBoardResponse])
def list_shared_with_me(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[SharedBoardResponse]:
    grants = (
        db.query(AccessGrant)
        .filter(AccessGrant.user_id == user_id, AccessGrant.status == "accepted")
        .order_by(AccessGrant.accepted_at.desc())
        .all()
    )
    result = []
    for grant in grants:
        board = db.query(Board).filter(Board.id == grant.board_id).first()
        if board is None:
            continue
        item_count = db.query(BoardItem).filter(BoardItem.board_id == board.id).count()
        result.append(
            SharedBoardResponse(
                id=board.id,
                name=board.name,
                owner_user_id=board.owner_user_id,
                owner_email=board.owner_email,
                owner_first_name=board.owner_first_name,
                role=grant.role,
                accepted_at=grant.accepted_at,
                item_count=item_count,
            )
        )
    return result


@app.get("/{board_id}", response_model=BoardWithItemsResponse)
def get_board(
    board_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BoardWithItemsResponse:
    board, role = _get_board_with_role(board_id, user_id, db)
    return _board_with_items_response(board, role, db)


@app.post("/{board_id}/items")
async def add_item(
    board_id: uuid.UUID,
    payload: AddItemRequest,
    auth: tuple[uuid.UUID, str] = Depends(get_current_user_id_and_token),
    db: Session = Depends(get_db),
) -> JSONResponse:
    user_id, token = auth
    board, role = _get_board_with_role(board_id, user_id, db)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the board owner can add items"
        )

    # Fetched with the caller's own token — since only the owner reaches
    # this point, this is the owner's token, correctly scoped to their own
    # items in Items' eyes (Decision #37).
    try:
        item = await fetch_item(payload.item_id, token)
    except ItemsServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Items service is unavailable — try again shortly",
        )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    board_item = BoardItem(
        board_id=board.id,
        item_id=payload.item_id,
        title=item["title"],
        url=item["url"],
        favicon_url=item.get("favicon_url"),
        preview_text=item.get("preview_text"),
        preview_media_url=item.get("preview_media_url"),
        tags=item.get("tags") or [],
    )
    db.add(board_item)

    try:
        db.commit()
    except IntegrityError:
        # Already on this board — idempotent success, not an error, same
        # philosophy as Items' ingest (Decision #33).
        db.rollback()
        board_item = (
            db.query(BoardItem)
            .filter(BoardItem.board_id == board.id, BoardItem.item_id == payload.item_id)
            .first()
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(BoardItemResponse.model_validate(board_item)),
        )

    db.refresh(board_item)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(BoardItemResponse.model_validate(board_item)),
    )


@app.delete("/{board_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    board_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    board, role = _get_board_with_role(board_id, user_id, db)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the board owner can remove items"
        )

    db.query(BoardItem).filter(
        BoardItem.board_id == board.id, BoardItem.item_id == item_id
    ).delete()
    db.commit()


@app.post("/{board_id}/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    board_id: uuid.UUID,
    payload: InviteRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> InviteResponse:
    board, role = _get_board_with_role(board_id, user_id, db)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only the board owner can invite"
        )

    now = datetime.now(timezone.utc)
    invited_email = payload.invited_email.lower()
    # A still-valid grant (pending or already accepted) for this email on
    # this board already exists — don't create a second, confusing one.
    # Scoped to non-expired only: an expired pending invite shouldn't block
    # re-inviting the same person.
    existing = (
        db.query(AccessGrant)
        .filter(
            AccessGrant.board_id == board.id,
            AccessGrant.invited_email == invited_email,
            AccessGrant.invite_token_expires_at >= now,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This board is already shared with that email",
        )

    token = generate_invite_token()
    expires_at = now + INVITE_TOKEN_TTL
    grant = AccessGrant(
        board_id=board.id,
        invited_email=invited_email,
        role="viewer",  # hardcoded — no role picker in v1 (Decision #10)
        invite_token_hash=hash_invite_token(token),
        invite_token_expires_at=expires_at,
    )
    db.add(grant)
    db.commit()

    return InviteResponse(
        board_id=board.id,
        invited_email=grant.invited_email,
        role=grant.role,
        invite_token=token,  # only ever visible unhashed, right here (Decision #36)
        expires_at=expires_at,
    )


@app.post("/invites/{token}/accept", response_model=BoardWithItemsResponse)
def accept_invite(
    token: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BoardWithItemsResponse:
    token_hash = hash_invite_token(token)
    grant = db.query(AccessGrant).filter(AccessGrant.invite_token_hash == token_hash).first()
    now = datetime.now(timezone.utc)

    if grant is None or grant.invite_token_expires_at < now:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found or expired")

    if grant.user_id is not None and grant.user_id != user_id:
        # Already claimed by someone else — token possession alone isn't
        # enough once a grant is locked to its first accepter (Decision
        # #39). Same 404 as "doesn't exist," not 403 — don't reveal that a
        # valid invite exists to someone it was never claimed by.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found or expired")

    if grant.user_id is None:
        grant.user_id = user_id
        grant.status = "accepted"
        grant.accepted_at = now
        db.commit()

    board = db.query(Board).filter(Board.id == grant.board_id).first()
    return _board_with_items_response(board, grant.role, db)
