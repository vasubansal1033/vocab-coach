"""srs_cards

Revision ID: a7d4e5f63b72
Revises: f6c3d4e52a61
Create Date: 2026-11-10 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7d4e5f63b72"
down_revision: str | Sequence[str] | None = "f6c3d4e52a61"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "srs_cards",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("option_id", sa.String(), nullable=False),
        sa.Column("fsrs_card", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["precision_options.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "option_id", name="uq_srs_cards_user_option"),
    )
    with op.batch_alter_table("srs_cards", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_srs_cards_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_srs_cards_option_id"), ["option_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_srs_cards_due_at"), ["due_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("srs_cards", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_srs_cards_due_at"))
        batch_op.drop_index(batch_op.f("ix_srs_cards_option_id"))
        batch_op.drop_index(batch_op.f("ix_srs_cards_user_id"))
    op.drop_table("srs_cards")
