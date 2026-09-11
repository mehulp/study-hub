import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Board(Base):
    __tablename__ = "boards"
    __table_args__ = {"schema": "board"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # Soft reference (Decision #14) — crosses into auth's schema.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Denormalized from Auth's /me at creation time (Decision #70) — nullable
    # at the DB level for pre-migration rows, but every board created going
    # forward always has one (create_board fails rather than proceed without
    # it, same pattern as add_item's 503-on-Items-unavailable).
    owner_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Same denormalization as owner_email (Decision #71), extended now that
    # /me also returns first_name (Decision #75).
    owner_first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BoardItem(Base):
    __tablename__ = "board_items"
    __table_args__ = {"schema": "board"}

    board_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("board.boards.id"), primary_key=True
    )
    # Soft reference — crosses into items' schema.
    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    # Denormalized display snapshot, captured at add-time (Decision #37) —
    # not a live reference to Items.
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AccessGrant(Base):
    __tablename__ = "access_grants"
    __table_args__ = {"schema": "board"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    board_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("board.boards.id"), nullable=False
    )
    invited_email: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable until accepted — soft reference, crosses into auth's schema.
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    invite_token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    invite_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
