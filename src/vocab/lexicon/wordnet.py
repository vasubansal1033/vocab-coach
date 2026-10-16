"""WordNet sense summaries for group_gen input (not suggestion source)."""

from __future__ import annotations

from nltk.corpus import wordnet as wn


def senses_for_lemma(lemma: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Return short sense dicts the draft prompt can list."""
    synsets = wn.synsets(lemma)
    out: list[dict[str, str]] = []
    for syn in synsets[:limit]:
        out.append(
            {
                "pos": syn.pos(),
                "definition": syn.definition(),
                "examples": "; ".join(syn.examples()[:2]),
            }
        )
    return out
