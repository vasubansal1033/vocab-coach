"""Cached spaCy pipeline; load once at process start, not per request."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from spacy.language import Language

_nlp: Language | None = None


def load() -> Language:
    """Load en_core_web_sm on first call and reuse it afterwards."""
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def get_nlp() -> Language:
    """Return the cached pipeline, loading it lazily if startup did not."""
    return load()
