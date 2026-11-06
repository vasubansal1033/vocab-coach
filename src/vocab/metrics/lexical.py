"""MTLD lexical diversity without an extra dependency."""

from __future__ import annotations

from collections.abc import Sequence

MTLD_THRESHOLD = 0.72
MTLD_MIN_WORDS = 100


def mtld(
    tokens: Sequence[str],
    *,
    threshold: float = MTLD_THRESHOLD,
    min_words: int = MTLD_MIN_WORDS,
) -> float | None:
    """Mean bidirectional MTLD; None when the sample is too short to trust."""
    if len(tokens) < min_words:
        return None
    forward = _mtld_one_way(tokens, threshold)
    backward = _mtld_one_way(list(reversed(tokens)), threshold)
    return (forward + backward) / 2.0


def _mtld_one_way(tokens: Sequence[str], threshold: float) -> float:
    """One MTLD pass: factors when TTR falls to the threshold, plus a partial tail."""
    if not tokens:
        return 0.0
    factors = 0.0
    types: set[str] = set()
    token_count = 0
    for token in tokens:
        types.add(token)
        token_count += 1
        ttr = len(types) / token_count
        if ttr <= threshold:
            factors += 1.0
            types = set()
            token_count = 0
    if token_count > 0:
        ttr = len(types) / token_count
        factors += (1.0 - ttr) / (1.0 - threshold)
    if factors == 0.0:
        return float(len(tokens))
    return len(tokens) / factors
