"""add replaced_by_id to auth.refresh_tokens for rotation + reuse detection

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column(
            "replaced_by_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth.refresh_tokens.id"),
            nullable=True,
        ),
        schema="auth",
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "replaced_by_id", schema="auth")
