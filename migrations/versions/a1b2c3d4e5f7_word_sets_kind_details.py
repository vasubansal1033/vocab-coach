"""precision_groups.kind, nullable head_lemma; precision_options.details

Revision ID: a1b2c3d4e5f7
Revises: a3b4c5d6e7f8
Create Date: 2026-11-11 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: str | Sequence[str] | None = "a3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("precision_groups", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("kind", sa.String(), nullable=False, server_default="precision")
        )
        batch_op.alter_column("head_lemma", existing_type=sa.String(), nullable=True)
    with op.batch_alter_table("precision_options", schema=None) as batch_op:
        batch_op.add_column(sa.Column("details", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("precision_options", schema=None) as batch_op:
        batch_op.drop_column("details")
    with op.batch_alter_table("precision_groups", schema=None) as batch_op:
        batch_op.alter_column("head_lemma", existing_type=sa.String(), nullable=False)
        batch_op.drop_column("kind")
