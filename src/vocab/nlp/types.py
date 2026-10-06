"""Typed results from the analyzer and learned-word matcher."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from spacy.tokens import Doc


Reason = Literal["crutch", "frequency"]


@dataclass(frozen=True)
class LemmaCount:
    """One surface form of a lemma and how often it appeared."""

    lemma: str
    surface: str
    count: int


@dataclass(frozen=True)
class CandidateSpan:
    """A vague span the editor may want to rewrite."""

    text: str
    start: int
    end: int
    lemma: str
    pos: str
    reason: Reason


@dataclass(frozen=True)
class Hit:
    """A learned option found in a user message."""

    text: str
    start: int
    end: int
    lemma: str


@dataclass
class Analysis:
    """Full analyzer output for one message.

    `doc` is kept so `find_learned_words` can reuse lemmas without re-parsing.
    """

    word_count: int
    lemma_counts: list[LemmaCount]
    candidates: list[CandidateSpan]
    doc: Doc = field(repr=False)
