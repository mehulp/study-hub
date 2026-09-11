"""add owner_email to boards

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Denormalized (same pattern as Decision #37's board_items snapshot),
    # captured once at board-creation time via Auth's /me using the
    # owner's own token -- not a live lookup, and not a new "resolve any
    # user's email" capability (Decision #70): a user can always ask Auth
    # about themselves.
    op.add_column("boards", sa.Column("owner_email", sa.Text(), nullable=True), schema="board")

    # One-time backfill for boards created before this column existed (the
    # Phase 4 demo board) -- a read-only cross-schema query to fix existing
    # data, not a persisted FK (Decision #14 only forbids the latter).
    op.execute(
        """
        UPDATE board.boards
        SET owner_email = auth.users.email
        FROM auth.users
        WHERE board.boards.owner_user_id = auth.users.id
        AND board.boards.owner_email IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("boards", "owner_email", schema="board")
