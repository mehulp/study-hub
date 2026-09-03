"""create board schema: boards, board_items, access_grants

Revision ID: 0001
Revises:
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE SCHEMA IF NOT EXISTS board")

    op.create_table(
        "boards",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Soft reference (Decision #14) — crosses into auth's schema.
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="board",
    )
    op.create_index("ix_board_boards_owner_user_id", "boards", ["owner_user_id"], schema="board")

    op.create_table(
        "board_items",
        # Real FK — same schema, Board service owns both sides (Decision #14).
        sa.Column(
            "board_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("board.boards.id"),
            nullable=False,
        ),
        # Soft reference — crosses into items' schema.
        sa.Column("item_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        # Denormalized display snapshot, captured at add-time via the
        # owner's own token (Decision #37) — not a live reference. Viewing
        # a board reads these directly; it never calls Items.
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("favicon_url", sa.Text(), nullable=True),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("preview_media_url", sa.Text(), nullable=True),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("board_id", "item_id"),
        schema="board",
    )

    op.create_table(
        "access_grants",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "board_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("board.boards.id"),
            nullable=False,
        ),
        sa.Column("invited_email", sa.Text(), nullable=False),
        # Nullable — filled in once the invite is accepted (Step 2's "two
        # real states" note: pending-by-email vs settled-by-user_id).
        # Soft reference — crosses into auth's schema.
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        # Hashed, not stored raw (Decision #36 — same pattern as refresh
        # tokens): the opaque token itself is only ever seen once, at
        # invite-creation time, in the response/email link.
        sa.Column("invite_token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("invite_token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('viewer', 'editor')", name="ck_access_grants_role"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted')", name="ck_access_grants_status"
        ),
        schema="board",
    )
    op.create_index(
        "ix_board_access_grants_board_id", "access_grants", ["board_id"], schema="board"
    )
    op.create_index(
        "ix_board_access_grants_user_id", "access_grants", ["user_id"], schema="board"
    )


def downgrade() -> None:
    op.drop_table("access_grants", schema="board")
    op.drop_table("board_items", schema="board")
    op.drop_table("boards", schema="board")
