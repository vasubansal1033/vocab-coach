"""lexicon tables

Revision ID: d4a1b2c30e4f
Revises: c3e8f1a90b2d
Create Date: 2026-11-10 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4a1b2c30e4f"
down_revision: str | Sequence[str] | None = "c3e8f1a90b2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "precision_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("head_lemma", sa.String(), nullable=False),
        sa.Column("pos", sa.String(), nullable=False),
        sa.Column("sense_gloss", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("precision_groups", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_precision_groups_head_lemma"), ["head_lemma"], unique=False
        )

    op.create_table(
        "precision_options",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("distinction", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("register", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["precision_groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("precision_options", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_precision_options_group_id"), ["group_id"], unique=False
        )

    op.create_table(
        "review_queue",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("editor_run_id", sa.String(), nullable=True),
        sa.Column("head_lemma", sa.String(), nullable=False),
        sa.Column("proposed_word", sa.String(), nullable=False),
        sa.Column("distinction", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("review_queue", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_review_queue_head_lemma"), ["head_lemma"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("review_queue", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_review_queue_head_lemma"))
    op.drop_table("review_queue")
    with op.batch_alter_table("precision_options", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_precision_options_group_id"))
    op.drop_table("precision_options")
    with op.batch_alter_table("precision_groups", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_precision_groups_head_lemma"))
    op.drop_table("precision_groups")
