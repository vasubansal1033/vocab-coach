"""conversation feedback_expectations

Revision ID: c9f7a8b95d94
Revises: b8e5f6a74c83
Create Date: 2026-11-11 19:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9f7a8b95d94"
down_revision: str | Sequence[str] | None = "b8e5f6a74c83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add optional per-conversation editor brief."""
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("feedback_expectations", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop feedback_expectations."""
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_column("feedback_expectations")
