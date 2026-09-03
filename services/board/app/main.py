import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user_id, get_current_user_id_and_token, load_public_key
from app.db import get_db
from app.items_client import fetch_item
from app.models import AccessGrant, Board, BoardItem
from app.schemas import (
    AddItemRequest,
    BoardItemResponse,
    BoardResponse,
    BoardWithItemsResponse,
    CreateBoardRequest,
)


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
def create_board(
    payload: CreateBoardRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Board:
    board = Board(owner_user_id=user_id, name=payload.name)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


@app.get("/{board_id}", response_model=BoardWithItemsResponse)
def get_board(
    board_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> BoardWithItemsResponse:
    board, role = _get_board_with_role(board_id, user_id, db)

    items = (
        db.query(BoardItem)
        .filter(BoardItem.board_id == board.id)
        .order_by(BoardItem.added_at.desc())
        .all()
    )
    return BoardWithItemsResponse(
        id=board.id,
        owner_user_id=board.owner_user_id,
        name=board.name,
        created_at=board.created_at,
        role=role,
        items=[BoardItemResponse.model_validate(i) for i in items],
    )


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
    item = await fetch_item(payload.item_id, token)
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
