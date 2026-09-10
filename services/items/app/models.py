import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "source", "external_id", name="uq_items_owner_source_external_id"),
        {"schema": "items"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    # Soft reference (Decision #14) — owner_user_id lives in auth's schema,
    # validated by application code (the JWT it came from), never a real FK.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    folder_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Personal commentary on a resource — Decision #64.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # delete-orphan: removing a tag from item.tags (e.g. PATCH replacing the
    # set) deletes that row. passive_deletes=True: when the *item itself* is
    # deleted, let Postgres's own ON DELETE CASCADE (migration 0002) clean up
    # item_tags rather than SQLAlchemy issuing its own SELECT+DELETE per row.
    # selectin: tags for a whole list of items load in one extra query, not
    # one query per item.
    tags: Mapped[list["ItemTag"]] = relationship(
        "ItemTag",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class ItemTag(Base):
    __tablename__ = "item_tags"
    __table_args__ = {"schema": "items"}

    # Real FK (Decision #14) — item_tags and items share the same schema.
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.items.id", ondelete="CASCADE"), primary_key=True
    )
    # Lowercased by application code before every write (Decision #62, same
    # pattern as auth.users.email — Decision #17), not a DB-level constraint.
    tag: Mapped[str] = mapped_column(Text, primary_key=True)
