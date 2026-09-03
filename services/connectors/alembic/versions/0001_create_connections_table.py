"""create connectors.connections table

Revision ID: 0001
Revises:
Create Date: 2026-09-04

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
    op.execute("CREATE SCHEMA IF NOT EXISTS connectors")

    op.create_table(
        "connections",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Soft reference (Decision #14) — crosses into auth's schema.
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        # Hashed, not stored raw (Decision #42) — nullable because Twitter
        # connections (not yet built) will use OAuth tokens instead.
        sa.Column("push_token_hash", sa.Text(), nullable=True, unique=True),
        sa.Column("oauth_access_token", sa.Text(), nullable=True),
        sa.Column("oauth_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "type IN ('twitter', 'browser_chrome', 'browser_firefox')",
            name="ck_connections_type",
        ),
        schema="connectors",
    )
    op.create_index(
        "ix_connectors_connections_owner_user_id",
        "connections",
        ["owner_user_id"],
        schema="connectors",
    )


def downgrade() -> None:
    op.drop_table("connections", schema="connectors")
