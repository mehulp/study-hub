"""add learning_plans.interviewpal_pack_key

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Optional pairing of a plan with an InterviewPal practice pack, by the pack's stable key. Nullable with no default,
    # so every existing plan simply has no pairing. Not constrained here: the API validates the supported keys, so adding
    # a pack later is a code change, not another migration.
    op.add_column(
        "learning_plans",
        sa.Column("interviewpal_pack_key", sa.Text(), nullable=True),
        schema="items",
    )


def downgrade() -> None:
    op.drop_column("learning_plans", "interviewpal_pack_key", schema="items")
