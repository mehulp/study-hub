"""add learning_plans and plan_items tables

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
    # Learning Plans (roadmap Phase 1, Decision #85) — deliberately new
    # tables in Items' own schema, not a new service: same "extend the
    # owning service" precedent as tags/notes (Decisions #62/#64), not the
    # Board-style separate-service treatment, since nothing about this
    # feature needs its own deployable, its own RBAC, or independent
    # scaling.
    op.create_table(
        "learning_plans",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Soft reference (Decision #14) — owner_user_id lives in auth's
        # schema, validated by application code (the JWT it came from),
        # same pattern as items.owner_user_id.
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="items",
    )
    op.create_index(
        "ix_learning_plans_owner_user_id",
        "learning_plans",
        ["owner_user_id"],
        schema="items",
    )

    # plan_items: a join table, but with real per-row state (status/order/
    # priority/target_date/estimated_effort), unlike board_items' simpler
    # membership-plus-display-snapshot shape. item_id is a REAL FK here --
    # unlike Board's item_id (a different service/schema, so it must be a
    # soft reference per Decision #14) -- because plan_items and items
    # share this same schema, the same reasoning item_tags already used.
    op.create_table(
        "plan_items",
        sa.Column(
            "plan_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.learning_plans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "item_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_started"),
        sa.Column("order_index", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("estimated_effort_minutes", sa.Integer(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'skipped')",
            name="ck_plan_items_status",
        ),
        sa.CheckConstraint(
            "priority IS NULL OR priority IN ('low', 'medium', 'high')",
            name="ck_plan_items_priority",
        ),
        schema="items",
    )
    # Supports "does this item already appear in this plan" (add-items
    # dialog exclusion, same UX as AddItemsToBoardDialog) and "all plans
    # containing this item" without a table scan.
    op.create_index(
        "ix_plan_items_item_id",
        "plan_items",
        ["item_id"],
        schema="items",
    )


def downgrade() -> None:
    op.drop_index("ix_plan_items_item_id", table_name="plan_items", schema="items")
    op.drop_table("plan_items", schema="items")
    op.drop_index("ix_learning_plans_owner_user_id", table_name="learning_plans", schema="items")
    op.drop_table("learning_plans", schema="items")
