"""Find uses of learned precision options in analyzed text."""

from __future__ import annotations

from collections.abc import Sequence

from spacy.matcher import PhraseMatcher

from vocab.nlp.model import get_nlp
from vocab.nlp.types import Analysis, Hit


def find_learned_words(
    analysis: Analysis,
    learned_option_lemmas: Sequence[str],
) -> list[Hit]:
    """Match learned option lemmas, including multi-word ones like 'work around'."""
    if not learned_option_lemmas:
        return []

    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    for option in learned_option_lemmas:
        # nlp() (not make_doc) so patterns carry lemmas for attr="LEMMA".
        matcher.add(option, [nlp(option)])

    hits: list[Hit] = []
    for match_id, start, end in matcher(analysis.doc):
        span = analysis.doc[start:end]
        lemma = nlp.vocab.strings[match_id]
        hits.append(
            Hit(
                text=span.text,
                start=span.start_char,
                end=span.end_char,
                lemma=lemma,
            )
        )
    return hits
