"""exercises and exercise_attempts

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-11-11 20:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "exercises",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("item_type", sa.String(), nullable=False),
        sa.Column("prompt", sa.JSON(), nullable=False),
        sa.Column("answer", sa.JSON(), nullable=False),
        sa.Column("llm_call_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["precision_groups.id"]),
        sa.ForeignKeyConstraint(["llm_call_id"], ["llm_calls.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_exercises_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_exercises_group_id"), ["group_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_exercises_item_type"), ["item_type"], unique=False)

    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("exercise_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("exercise_attempts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_exercise_attempts_exercise_id"), ["exercise_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_exercise_attempts_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("exercise_attempts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_exercise_attempts_user_id"))
        batch_op.drop_index(batch_op.f("ix_exercise_attempts_exercise_id"))
    op.drop_table("exercise_attempts")
    with op.batch_alter_table("exercises", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_exercises_item_type"))
        batch_op.drop_index(batch_op.f("ix_exercises_group_id"))
        batch_op.drop_index(batch_op.f("ix_exercises_user_id"))
    op.drop_table("exercises")
