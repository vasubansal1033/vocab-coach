"""conversation flow_mode and allow_idioms

Revision ID: e1b2c3d4e5f6
Revises: d0a1b2c3d4e5
Create Date: 2026-11-11 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add flow_mode and allow_idioms; both default false and are fixed at creation."""
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("flow_mode", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("allow_idioms", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Drop flow_mode and allow_idioms."""
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_column("allow_idioms")
        batch_op.drop_column("flow_mode")
