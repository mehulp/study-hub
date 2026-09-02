"""create items.items table

Revision ID: 0001
Revises:
Create Date: 2026-09-02

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
    # Own migration history stands alone (Decision #19) — pgcrypto is
    # instance-wide and likely already enabled by auth's migrations on this
    # shared Postgres instance, but IF NOT EXISTS makes this migration
    # correct even run against a fresh database on its own.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE SCHEMA IF NOT EXISTS items")

    op.create_table(
        "items",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Soft reference, not a real FK — owner_user_id crosses into auth's
        # schema, which Decision #14 forbids a real FK across (a true
        # database-per-service split couldn't have one either).
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("folder_path", sa.Text(), nullable=True),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("preview_media_url", sa.Text(), nullable=True),
        sa.Column("favicon_url", sa.Text(), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="items",
    )
    op.create_unique_constraint(
        "uq_items_owner_source_external_id",
        "items",
        ["owner_user_id", "source", "external_id"],
        schema="items",
    )
    # Supports "list my items, optionally filtered by source" (the actual
    # query shape both the dashboard and Board's composition read will use).
    op.create_index(
        "ix_items_owner_user_id_source",
        "items",
        ["owner_user_id", "source"],
        schema="items",
    )


def downgrade() -> None:
    op.drop_index("ix_items_owner_user_id_source", table_name="items", schema="items")
    op.drop_table("items", schema="items")
