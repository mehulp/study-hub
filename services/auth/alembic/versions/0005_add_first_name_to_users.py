"""add first_name to auth.users

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable at the DB level (UI redesign spec) so existing users --
    # including the two real seeded demo accounts (Decision #67) -- keep
    # working unchanged; the frontend falls back to a neutral "Welcome back"
    # when it's null rather than deriving a name from the email.
    op.add_column("users", sa.Column("first_name", sa.Text(), nullable=True), schema="auth")


def downgrade() -> None:
    op.drop_column("users", "first_name", schema="auth")
