"""add owner_first_name to boards

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-11

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
    # Same denormalization pattern as owner_email (Decision #71), extended
    # now that Auth's /me also returns first_name (Decision #73) -- one
    # more field from a call Board already makes at board-creation time,
    # not a new capability. Nullable: pre-existing boards get backfilled
    # from whatever auth.users.first_name already holds (often still null,
    # since first_name itself is optional -- the frontend falls back to
    # owner_email either way).
    op.add_column("boards", sa.Column("owner_first_name", sa.Text(), nullable=True), schema="board")

    op.execute(
        """
        UPDATE board.boards
        SET owner_first_name = auth.users.first_name
        FROM auth.users
        WHERE board.boards.owner_user_id = auth.users.id
        AND board.boards.owner_first_name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("boards", "owner_first_name", schema="board")
