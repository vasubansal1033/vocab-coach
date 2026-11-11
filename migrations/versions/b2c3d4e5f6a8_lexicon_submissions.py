"""lexicon_submissions for idempotent user batch ingest

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-11-11 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store replayable batch lexicon submissions per user."""
    op.create_table(
        "lexicon_submissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_lexicon_submissions_user_idempotency_key",
        ),
    )
    with op.batch_alter_table("lexicon_submissions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_lexicon_submissions_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_lexicon_submissions_idempotency_key"),
            ["idempotency_key"],
            unique=False,
        )


def downgrade() -> None:
    """Drop lexicon_submissions."""
    with op.batch_alter_table("lexicon_submissions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_lexicon_submissions_idempotency_key"))
        batch_op.drop_index(batch_op.f("ix_lexicon_submissions_user_id"))
    op.drop_table("lexicon_submissions")
