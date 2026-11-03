"""drills and drill_attempts

Revision ID: b8e5f6a74c83
Revises: a7d4e5f63b72
Create Date: 2026-11-10 23:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8e5f6a74c83"
down_revision: str | Sequence[str] | None = "a7d4e5f63b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "drills",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("vague_sentence", sa.Text(), nullable=False),
        sa.Column("intended_option_id", sa.String(), nullable=False),
        sa.Column("intended_word", sa.String(), nullable=False),
        sa.Column("llm_call_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["precision_groups.id"]),
        sa.ForeignKeyConstraint(["llm_call_id"], ["llm_calls.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("drills", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_drills_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_drills_group_id"), ["group_id"], unique=False)

    op.create_table(
        "drill_attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("drill_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("grade", sa.JSON(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("llm_call_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["drill_id"], ["drills.id"]),
        sa.ForeignKeyConstraint(["llm_call_id"], ["llm_calls.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("drill_attempts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_drill_attempts_drill_id"), ["drill_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_drill_attempts_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("drill_attempts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_drill_attempts_user_id"))
        batch_op.drop_index(batch_op.f("ix_drill_attempts_drill_id"))
    op.drop_table("drill_attempts")
    with op.batch_alter_table("drills", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_drills_group_id"))
        batch_op.drop_index(batch_op.f("ix_drills_user_id"))
    op.drop_table("drills")
