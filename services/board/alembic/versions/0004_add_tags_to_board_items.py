"""add tags to board_items

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widens Decision #37's denormalized snapshot (title/url/favicon_url/
    # preview_*) to also capture tags at add-time -- tags didn't exist yet
    # (Decision #62) when that snapshot was originally designed, so this
    # was a real gap, not a deliberate omission. Same pattern as everything
    # else on this row: copied once when an item is added to a board, not a
    # live reference.
    op.add_column(
        "board_items",
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        schema="board",
    )

    # Backfill existing rows from Items' current tags -- a one-time cross-
    # schema read (same instance, no FK, Decision #14), not a live link
    # going forward.
    op.execute(
        """
        UPDATE board.board_items
        SET tags = COALESCE(agg.tags, '{}')
        FROM (
            SELECT item_id, array_agg(tag ORDER BY tag) AS tags
            FROM items.item_tags
            GROUP BY item_id
        ) AS agg
        WHERE board.board_items.item_id = agg.item_id
        """
    )


def downgrade() -> None:
    op.drop_column("board_items", "tags", schema="board")
