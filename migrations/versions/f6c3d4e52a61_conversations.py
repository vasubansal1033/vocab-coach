"""conversations, messages, lemma counts; editor_runs FK

Revision ID: f6c3d4e52a61
Revises: e5b2c3d41f50
Create Date: 2026-11-10 19:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6c3d4e52a61"
down_revision: str | Sequence[str] | None = "e5b2c3d41f50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_conversations_user_id"), ["user_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("conversation_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_messages_conversation_id"), ["conversation_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_messages_user_id"), ["user_id"], unique=False)

    op.create_table(
        "message_lemma_counts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("message_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("lemma", sa.String(), nullable=False),
        sa.Column("surface", sa.String(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id", "lemma", "surface", name="uq_lemma_counts_msg_lemma_surface"
        ),
    )
    with op.batch_alter_table("message_lemma_counts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_message_lemma_counts_message_id"), ["message_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_message_lemma_counts_user_id"), ["user_id"], unique=False
        )

    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_editor_runs_message_id",
            "messages",
            ["message_id"],
            ["id"],
        )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_suggestions_message_id",
            "messages",
            ["message_id"],
            ["id"],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_suggestions_message_id", type_="foreignkey")
    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_editor_runs_message_id", type_="foreignkey")
    with op.batch_alter_table("message_lemma_counts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_message_lemma_counts_user_id"))
        batch_op.drop_index(batch_op.f("ix_message_lemma_counts_message_id"))
    op.drop_table("message_lemma_counts")
    with op.batch_alter_table("messages", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_messages_user_id"))
        batch_op.drop_index(batch_op.f("ix_messages_conversation_id"))
    op.drop_table("messages")
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_conversations_user_id"))
    op.drop_table("conversations")
