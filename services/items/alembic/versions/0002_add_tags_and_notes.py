"""add item_tags table and items.notes column

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10

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
    # Personal commentary on a resource — Decision #64. Nullable: notes are
    # optional at save time, same as the schema's other per-source fields.
    op.add_column(
        "items",
        sa.Column("notes", sa.Text(), nullable=True),
        schema="items",
    )

    # Free-text, multi-valued tags — Decision #62. No separate `tags`
    # identity table: nothing here needs tag metadata or an atomic
    # rename-everywhere operation, so a plain join table storing the raw
    # string is enough. `tag` is lowercased by application code before every
    # write (mirrors auth.users.email — Decision #17), not enforced here,
    # since Postgres text comparison is case-sensitive by default.
    op.create_table(
        "item_tags",
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            # Real FK (Decision #14) — item_tags and items share the same
            # schema, unlike owner_user_id's cross-schema soft reference
            # above. CASCADE: a tag row means nothing once its item is gone.
            sa.ForeignKey("items.items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("tag", sa.Text(), primary_key=True),
        schema="items",
    )
    # Supports "which items have tag X" (browse-by-tag) and "distinct tags
    # this owner has used" (autocomplete) without a full table scan.
    op.create_index(
        "ix_item_tags_tag",
        "item_tags",
        ["tag"],
        schema="items",
    )


def downgrade() -> None:
    op.drop_index("ix_item_tags_tag", table_name="item_tags", schema="items")
    op.drop_table("item_tags", schema="items")
    op.drop_column("items", "notes", schema="items")
