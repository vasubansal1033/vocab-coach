"""Load the crutch-word list used to force-mark vague lemmas."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

# Repo-root data file; kept outside the package so seeds are easy to edit.
_CRUTCH_PATH = Path(__file__).resolve().parents[3] / "data" / "crutch_words.yaml"

# Frequency-rule only: common function ADVs that would otherwise match every sentence.
FREQUENCY_ADV_STOPLIST: frozenset[str] = frozenset(
    {
        "not",
        "so",
        "then",
        "also",
        "just",
        "too",
        "only",
        "even",
        "still",
        "already",
        "always",
        "never",
        "ever",
        "here",
        "there",
        "now",
        "yet",
    }
)

ZIPF_THRESHOLD = 5.5


@lru_cache
def crutch_entries() -> frozenset[tuple[str, str]]:
    """Return {(lemma, POS)} pairs from the seed YAML."""
    raw = yaml.safe_load(_CRUTCH_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"expected a list in {_CRUTCH_PATH}")
    entries: set[tuple[str, str]] = set()
    for item in raw:
        lemma = str(item["lemma"]).lower()
        pos = str(item["pos"]).upper()
        entries.add((lemma, pos))
    return frozenset(entries)


def is_crutch(lemma: str, pos: str) -> bool:
    """True when this lemma+POS pair is on the crutch list."""
    return (lemma.lower(), pos.upper()) in crutch_entries()
