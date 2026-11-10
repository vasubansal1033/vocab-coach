"""FK from editor_runs/suggestions.message_id to messages.id

Revision ID: d0a1b2c3d4e5
Revises: c9f7a8b95d94
Create Date: 2026-11-11 19:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0a1b2c3d4e5"
down_revision: str | Sequence[str] | None = "c9f7a8b95d94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Attach message_id FKs. Orphans are deleted first; app cleanup stays explicit."""
    conn = op.get_bind()
    # SQLite batch rebuild drops tables; child FKs require this off during recreate.
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        sa.text(
            "DELETE FROM suggestion_options WHERE suggestion_id IN "
            "(SELECT id FROM suggestions WHERE message_id NOT IN (SELECT id FROM messages))"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM suggestions WHERE message_id NOT IN (SELECT id FROM messages)"
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM editor_runs WHERE message_id NOT IN (SELECT id FROM messages)"
        )
    )
    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_editor_runs_message_id_messages",
            "messages",
            ["message_id"],
            ["id"],
        )
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_suggestions_message_id_messages",
            "messages",
            ["message_id"],
            ["id"],
        )
    conn.execute(sa.text("PRAGMA foreign_keys=ON"))


def downgrade() -> None:
    """Drop message_id foreign keys."""
    conn = op.get_bind()
    conn.execute(sa.text("PRAGMA foreign_keys=OFF"))
    with op.batch_alter_table("suggestions", schema=None) as batch_op:
        batch_op.drop_constraint("fk_suggestions_message_id_messages", type_="foreignkey")
    with op.batch_alter_table("editor_runs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_editor_runs_message_id_messages", type_="foreignkey")
    conn.execute(sa.text("PRAGMA foreign_keys=ON"))
