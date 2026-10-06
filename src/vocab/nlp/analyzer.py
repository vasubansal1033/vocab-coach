"""Mark vague spans and count lemmas in a user message."""

from __future__ import annotations

from collections import Counter

from spacy.tokens import Doc, Token
from wordfreq import zipf_frequency

from vocab.nlp.crutch import (
    FREQUENCY_ADV_STOPLIST,
    ZIPF_THRESHOLD,
    is_crutch,
)
from vocab.nlp.model import get_nlp
from vocab.nlp.types import Analysis, CandidateSpan, LemmaCount, Reason


def analyze(text: str) -> Analysis:
    """Tokenise text, count lemmas, and mark candidate vague spans."""
    doc = get_nlp()(text)
    lemma_counts = _count_lemmas(doc)
    word_count = sum(1 for token in doc if token.is_alpha)
    candidates = _candidate_spans(doc)
    return Analysis(
        word_count=word_count,
        lemma_counts=lemma_counts,
        candidates=candidates,
        doc=doc,
    )


def _count_lemmas(doc: Doc) -> list[LemmaCount]:
    """Count each (lemma, surface) pair; surface is what the user wrote."""
    counts: Counter[tuple[str, str]] = Counter()
    for token in doc:
        if not token.is_alpha:
            continue
        counts[(token.lemma_, token.text)] += 1
    return [
        LemmaCount(lemma=lemma, surface=surface, count=count)
        for (lemma, surface), count in sorted(counts.items())
    ]


def _is_frequency_candidate(token: Token) -> bool:
    """Adjectives and adverbs above the Zipf cut, excluding function ADVs."""
    if token.pos_ not in {"ADJ", "ADV"}:
        return False
    if token.pos_ == "ADV" and token.lemma_.lower() in FREQUENCY_ADV_STOPLIST:
        return False
    return zipf_frequency(token.lemma_, "en") >= ZIPF_THRESHOLD


def _token_reason(token: Token) -> Reason | None:
    """Why a single token is a candidate, or None if it is not."""
    if is_crutch(token.lemma_, token.pos_):
        return "crutch"
    # Verbs only through the crutch list; frequency would mark have/be everywhere.
    if _is_frequency_candidate(token):
        return "frequency"
    return None


def _candidate_spans(doc: Doc) -> list[CandidateSpan]:
    """Build non-overlapping spans, expanding intensifier+ADJ and ADJ+NOUN."""
    reasons: dict[int, Reason] = {}
    for token in doc:
        reason = _token_reason(token)
        if reason is not None:
            reasons[token.i] = reason

    spans: list[CandidateSpan] = []
    used: set[int] = set()

    # Expand ADJ candidates first so longer spans win over their parts.
    for index in sorted(reasons):
        token = doc[index]
        if token.pos_ != "ADJ":
            continue
        start = index
        end = index + 1
        if (
            index > 0
            and doc[index - 1].pos_ == "ADV"
            and is_crutch(doc[index - 1].lemma_, doc[index - 1].pos_)
        ):
            start = index - 1
        if end < len(doc) and doc[end].pos_ == "NOUN":
            end = end + 1
        spans.append(_span_from_range(doc, start, end, token.lemma_, token.pos_, reasons[index]))
        used.update(range(start, end))

    for index in sorted(reasons):
        if index in used:
            continue
        token = doc[index]
        spans.append(
            _span_from_range(doc, index, index + 1, token.lemma_, token.pos_, reasons[index])
        )
        used.add(index)

    spans.sort(key=lambda span: span.start)
    return spans


def _span_from_range(
    doc: Doc,
    start: int,
    end: int,
    lemma: str,
    pos: str,
    reason: Reason,
) -> CandidateSpan:
    """Slice character offsets from the Doc so the UI can highlight exactly."""
    span = doc[start:end]
    return CandidateSpan(
        text=span.text,
        start=span.start_char,
        end=span.end_char,
        lemma=lemma,
        pos=pos,
        reason=reason,
    )
