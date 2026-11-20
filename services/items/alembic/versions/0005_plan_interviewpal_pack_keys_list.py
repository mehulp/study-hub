"""learning_plans.interviewpal_pack_keys: a plan can be paired with several InterviewPal packs

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One pack per plan (0004) becomes an ordered list, so a week can have several daily practice packs. The list is NOT NULL
    # with an empty default (every plan simply has no pairing), and existing single pairings are carried over.
    #
    # EXPAND ONLY: the old single-key column (0004) is deliberately KEPT, and the application keeps it equal to the first pack
    # of the list, so the previous release of the items service still works against this schema (a code rollback needs no
    # database rollback). Drop it in a later migration, once no release before 0005 can run again. As in 0004, the supported
    # keys are checked by the API, not here.
    op.add_column(
        "learning_plans",
        sa.Column("interviewpal_pack_keys", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema="items",
    )
    op.execute(
        "UPDATE items.learning_plans SET interviewpal_pack_keys = jsonb_build_array(interviewpal_pack_key) "
        "WHERE interviewpal_pack_key IS NOT NULL"
    )


def downgrade() -> None:
    # The single-key column was never removed and is kept in sync, so only the list goes (any packs after the first are lost).
    op.drop_column("learning_plans", "interviewpal_pack_keys", schema="items")
