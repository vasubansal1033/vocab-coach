"""editor runs, suggestions, events

Revision ID: e5b2c3d41f50
Revises: d4a1b2c30e4f
Create Date: 2026-11-10 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5b2c3d41f50"
down_revision: str | Sequence[str] | None = "d4a1b2c30e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("subject_type", sa.String(), nullable=False),
        sa.Column("subject_id", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_events_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_events_type"), ["type"], unique=False)

    op.create_table(
        "editor_runs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("llm_call_id", sa.String(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["llm_call_id"], ["llm_calls.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_editor_runs_message_id"), ["message_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_editor_runs_user_id"), ["user_id"], unique=False)

    op.create_table(
        "suggestions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("editor_run_id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("original_text", sa.String(), nullable=False),
        sa.Column("span_start", sa.Integer(), nullable=False),
        sa.Column("span_end", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["editor_run_id"], ["editor_runs.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["precision_groups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_suggestions_editor_run_id"), ["editor_run_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_suggestions_message_id"), ["message_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_suggestions_user_id"), ["user_id"], unique=False)

    op.create_table(
        "suggestion_options",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("suggestion_id", sa.String(), nullable=False),
        sa.Column("option_id", sa.String(), nullable=True),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["option_id"], ["precision_options.id"]),
        sa.ForeignKeyConstraint(["suggestion_id"], ["suggestions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("suggestion_options", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_suggestion_options_suggestion_id"),
            ["suggestion_id"],
            unique=False,
        )

    with op.batch_alter_table("review_queue", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_review_queue_editor_run_id",
            "editor_runs",
            ["editor_run_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("review_queue", schema=None) as batch_op:
        batch_op.drop_constraint("fk_review_queue_editor_run_id", type_="foreignkey")
    with op.batch_alter_table("suggestion_options", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_suggestion_options_suggestion_id"))
    op.drop_table("suggestion_options")
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_suggestions_user_id"))
        batch_op.drop_index(batch_op.f("ix_suggestions_message_id"))
        batch_op.drop_index(batch_op.f("ix_suggestions_editor_run_id"))
    op.drop_table("suggestions")
    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_editor_runs_user_id"))
        batch_op.drop_index(batch_op.f("ix_editor_runs_message_id"))
    op.drop_table("editor_runs")
    with op.batch_alter_table("events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_events_type"))
        batch_op.drop_index(batch_op.f("ix_events_user_id"))
    op.drop_table("events")
