"""Done-when checks for the language analyzer."""

import pytest

from vocab.nlp.analyzer import analyze
from vocab.nlp.model import load


@pytest.fixture(scope="module", autouse=True)
def _nlp_model() -> None:
    """Fail clearly when setup-nlp has not been run."""
    try:
        load()
    except OSError as exc:
        pytest.fail(f"spaCy model missing; run `uv run vocab setup-nlp` first: {exc}")


GOLDEN = (
    "Yeah the migration was really hard and we had a big problem with the old data, "
    "but we fixed it in the end."
)


def test_golden_sentence_marks_expected_spans() -> None:
    analysis = analyze(GOLDEN)
    texts = {span.text.lower() for span in analysis.candidates}

    assert "really hard" in texts
    assert "big problem" in texts
    assert "fixed" in texts
    assert "migration" not in texts
    assert "data" not in texts
    assert "had" not in texts
