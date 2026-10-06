"""Done-when checks for learned-word matching."""

import pytest

from vocab.nlp.analyzer import analyze
from vocab.nlp.model import load
from vocab.nlp.usage import find_learned_words


@pytest.fixture(scope="module", autouse=True)
def _nlp_model() -> None:
    """Fail clearly when setup-nlp has not been run."""
    try:
        load()
    except OSError as exc:
        pytest.fail(f"spaCy model missing; run `uv run vocab setup-nlp` first: {exc}")


def test_find_learned_words_matches_work_around() -> None:
    analysis = analyze("We worked around it")
    hits = find_learned_words(analysis, ["work around"])
    assert len(hits) == 1
    assert "work" in hits[0].text.lower()
    assert "around" in hits[0].text.lower()
