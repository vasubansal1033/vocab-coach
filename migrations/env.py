"""Alembic environment: URL from app settings, batch mode for SQLite."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from vocab import events as _events  # noqa: F401  registers tables
from vocab.auth import models as _auth_models  # noqa: F401  registers tables
from vocab.config import get_settings
from vocab.conversation import models as _conversation_models  # noqa: F401  registers tables
from vocab.db import Base, make_engine
from vocab.drills import models as _drills_models  # noqa: F401  registers tables
from vocab.editor import models as _editor_models  # noqa: F401  registers tables
from vocab.exercises import models as _exercises_models  # noqa: F401  registers tables
from vocab.lexicon import models as _lexicon_models  # noqa: F401  registers tables
from vocab.llm import models as _llm_models  # noqa: F401  registers tables
from vocab.practice import models as _practice_models  # noqa: F401  registers tables

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importing model modules here (as later sections add them) registers their tables.
target_metadata = Base.metadata

DATABASE_URL = get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL without a live connection."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migrate through the app's own engine factory so SQLite pragmas match runtime."""
    connectable = make_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
