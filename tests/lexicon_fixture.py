"""Seed approved lexicon rows for tests (API/catalog path, no YAML)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from vocab.lexicon.ingest import import_builtin_catalog


def seed_lexicon(session: Session) -> dict[str, int]:
    """Import the built-in catalog as approved groups."""
    return import_builtin_catalog(session, source="seed")
