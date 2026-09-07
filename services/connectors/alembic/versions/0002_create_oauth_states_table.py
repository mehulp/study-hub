"""create connectors.oauth_states table

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07

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
    op.create_table(
        "oauth_states",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Random, unguessable, looked up by exact value at callback time —
        # no need to hash: this is a short-lived (10 min), single-use,
        # opaque CSRF token, not a credential that grants access to
        # anything by itself once expired/consumed (unlike a refresh or
        # push token, which stays valid for weeks).
        sa.Column("state", sa.Text(), nullable=False, unique=True),
        sa.Column("owner_user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        # PKCE's whole point: this value never goes over the wire to X
        # except at the final token-exchange step, so it has to be held
        # somewhere server-side between the authorize redirect and the
        # callback — this table is that "somewhere."
        sa.Column("code_verifier", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="connectors",
    )


def downgrade() -> None:
    op.drop_table("oauth_states", schema="connectors")
