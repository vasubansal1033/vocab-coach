"""Database engine, session dependency and the declarative base."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from vocab.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models; Alembic autogenerate reads its metadata."""


def _set_sqlite_pragmas(dbapi_connection, _record) -> None:  # noqa: ANN001
    """SQLite ignores foreign keys unless this is set on every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def make_engine(url: str, **kwargs) -> Engine:  # noqa: ANN003
    """Create an engine and, for SQLite, install the pragma listener.

    The listener is attached to this engine only, so tests can build their own.
    """
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, **kwargs)
    if parsed.get_backend_name() == "sqlite":
        event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


_engine: Engine | None = None
_sessionmaker: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Build the process-wide engine on first use, so import has no side effects."""
    global _engine, _sessionmaker
    if _engine is None:
        _engine = make_engine(get_settings().database_url)
        _sessionmaker = sessionmaker(_engine, expire_on_commit=False)
    return _engine


def set_pg_user_context(session: Session, user_id: str) -> None:
    """Set app.current_user_id for Postgres RLS policies; no-op on SQLite."""
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": user_id},
    )


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding one session per request."""
    get_engine()
    assert _sessionmaker is not None
    with _sessionmaker() as session:
        yield session
