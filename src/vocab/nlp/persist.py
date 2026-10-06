"""Shape analyzer output for the message tables added in Conversation UI."""

from __future__ import annotations

from typing import Any

from vocab.nlp.types import Analysis


def word_count_value(analysis: Analysis) -> int:
    """Return the word_count column value for a messages row."""
    return analysis.word_count


def lemma_count_rows(analysis: Analysis) -> list[dict[str, Any]]:
    """Return dicts ready to insert into message_lemma_counts later."""
    return [
        {"lemma": item.lemma, "surface": item.surface, "count": item.count}
        for item in analysis.lemma_counts
    ]
