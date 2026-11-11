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


def test_find_learned_words_matches_cutting_corners() -> None:
    analysis = analyze("We were cutting corners on testing")
    hits = find_learned_words(analysis, ["cut corners"])
    assert len(hits) == 1
    assert hits[0].lemma == "cut corners"


def test_find_learned_words_matches_see_eye_to_eye() -> None:
    analysis = analyze("They saw eye to eye on scope")
    hits = find_learned_words(analysis, ["see eye to eye"])
    assert len(hits) == 1
    assert hits[0].lemma == "see eye to eye"
