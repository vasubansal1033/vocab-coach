"""drills.context and drill_attempts.hints_used

Revision ID: f2a3b4c5d6e7
Revises: e1b2c3d4e5f6
Create Date: 2026-11-11 20:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "e1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("drills", schema=None) as batch_op:
        batch_op.add_column(sa.Column("context", sa.Text(), nullable=True))
    with op.batch_alter_table("drill_attempts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("drill_attempts", schema=None) as batch_op:
        batch_op.drop_column("hints_used")
    with op.batch_alter_table("drills", schema=None) as batch_op:
        batch_op.drop_column("context")
