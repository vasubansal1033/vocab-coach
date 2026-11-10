"""Copy all rows from a SQLite URL to a Postgres URL after migrations."""

from __future__ import annotations

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine


def copy_sqlite_to_postgres(*, sqlite_url: str, postgres_url: str) -> dict[str, int]:
    """Table-by-table copy. Target tables must already exist (Alembic upgrade)."""
    src = create_engine(sqlite_url)
    dst = create_engine(postgres_url)
    meta = MetaData()
    meta.reflect(bind=src)
    counts: dict[str, int] = {}
    with src.connect() as sconn, dst.begin() as dconn:
        # Parent tables before children; alphabetical is not enough, so disable FKs briefly.
        dconn.execute(text("SET session_replication_role = replica"))
        for table in meta.sorted_tables:
            rows = list(sconn.execute(table.select()).mappings())
            if not rows:
                counts[table.name] = 0
                continue
            dconn.execute(table.insert(), rows)
            counts[table.name] = len(rows)
        dconn.execute(text("SET session_replication_role = DEFAULT"))
    src.dispose()
    dst.dispose()
    return counts


def ping_engine(url: str) -> None:
    """Fail fast if the URL is unreachable."""
    engine: Engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()
