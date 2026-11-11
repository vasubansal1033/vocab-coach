"""Per-user metric queries over a date window; every filter includes user_id."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from wordfreq import word_frequency

from vocab.conversation.models import Message, MessageLemmaCount
from vocab.drills.models import DrillAttempt
from vocab.editor.models import EditorRun, Suggestion
from vocab.events import Event
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
from vocab.llm.models import LlmCall
from vocab.metrics.lexical import mtld
from vocab.nlp.crutch import crutch_entries

_WORD_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class WeekRate:
    """One weekly bucket ending at `end` (label = end date ISO)."""

    label: str
    end: datetime
    rate: float | None


@dataclass(frozen=True)
class WeekScore:
    label: str
    end: datetime
    score: float | None


@dataclass(frozen=True)
class GroupRef:
    id: str
    sense_gloss: str


@dataclass(frozen=True)
class OveruseRow:
    word: str
    uses: int
    lift: float
    groups: list[GroupRef]


@dataclass(frozen=True)
class OptionUsage:
    option_id: str
    word: str
    uses: int
    correct_uses: int


@dataclass(frozen=True)
class LemmaDetail:
    lemma: str
    weekly: list[WeekRate]
    options: list[OptionUsage]


def _crutch_lemmas() -> frozenset[str]:
    return frozenset(lemma for lemma, _pos in crutch_entries())


def _week_ends(start: datetime, end: datetime) -> list[datetime]:
    """Inclusive weekly bucket ends in (start, end], aligned to `end`."""
    ends: list[datetime] = []
    cursor = end
    while cursor > start:
        ends.append(cursor)
        cursor = cursor - timedelta(days=7)
    ends.reverse()
    return ends


def _user_messages(session: Session, user_id: str, start: datetime, end: datetime) -> list[Message]:
    stmt = (
        select(Message)
        .where(
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= start,
            Message.created_at < end,
        )
        .order_by(Message.created_at)
    )
    return list(session.scalars(stmt))


def _total_words(session: Session, user_id: str, start: datetime, end: datetime) -> int:
    value = session.scalar(
        select(func.coalesce(func.sum(Message.word_count), 0)).where(
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= start,
            Message.created_at < end,
        )
    )
    return int(value or 0)


def _crutch_hits(
    session: Session,
    user_id: str,
    start: datetime,
    end: datetime,
    *,
    lemma: str | None = None,
) -> int:
    lemmas = _crutch_lemmas()
    stmt = (
        select(func.coalesce(func.sum(MessageLemmaCount.count), 0))
        .join(Message, Message.id == MessageLemmaCount.message_id)
        .where(
            MessageLemmaCount.user_id == user_id,
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= start,
            Message.created_at < end,
            MessageLemmaCount.lemma.in_(lemmas),
        )
    )
    if lemma is not None:
        stmt = stmt.where(MessageLemmaCount.lemma == lemma.lower())
    return int(session.scalar(stmt) or 0)


def crutch_rate(session: Session, user_id: str, start: datetime, end: datetime) -> float | None:
    """1000 × crutch-lemma occurrences ÷ user words; None with no words."""
    words = _total_words(session, user_id, start, end)
    if words == 0:
        return None
    return 1000.0 * _crutch_hits(session, user_id, start, end) / words


def crutch_rate_for_lemma(
    session: Session, user_id: str, start: datetime, end: datetime, lemma: str
) -> float | None:
    words = _total_words(session, user_id, start, end)
    if words == 0:
        return None
    return 1000.0 * _crutch_hits(session, user_id, start, end, lemma=lemma) / words


def crutch_rate_weekly(
    session: Session, user_id: str, start: datetime, end: datetime
) -> list[WeekRate]:
    rows: list[WeekRate] = []
    for week_end in _week_ends(start, end):
        week_start = week_end - timedelta(days=7)
        bucket_start = max(week_start, start)
        rate = crutch_rate(session, user_id, bucket_start, week_end)
        rows.append(WeekRate(label=week_end.date().isoformat(), end=week_end, rate=rate))
    return rows


def overuse_lift(
    session: Session,
    user_id: str,
    start: datetime,
    end: datetime,
    *,
    limit: int = 10,
    min_uses: int = 5,
) -> list[OveruseRow]:
    """Surface forms used far more than wordfreq baseline, with matching groups."""
    words_total = _total_words(session, user_id, start, end)
    if words_total == 0:
        return []
    stmt = (
        select(
            MessageLemmaCount.surface,
            func.sum(MessageLemmaCount.count).label("uses"),
        )
        .join(Message, Message.id == MessageLemmaCount.message_id)
        .where(
            MessageLemmaCount.user_id == user_id,
            Message.user_id == user_id,
            Message.role == "user",
            Message.created_at >= start,
            Message.created_at < end,
        )
        .group_by(MessageLemmaCount.surface)
        .having(func.sum(MessageLemmaCount.count) >= min_uses)
    )
    rows: list[OveruseRow] = []
    for surface, uses in session.execute(stmt):
        word = str(surface)
        freq = word_frequency(word.lower(), "en")
        if freq <= 0:
            continue
        lift = (int(uses) / words_total) / freq
        groups = _groups_for_head(session, word.lower())
        rows.append(OveruseRow(word=word, uses=int(uses), lift=lift, groups=groups))
    rows.sort(key=lambda r: r.lift, reverse=True)
    return rows[:limit]


def _groups_for_head(session: Session, head_lemma: str) -> list[GroupRef]:
    stmt = select(PrecisionGroup).where(
        PrecisionGroup.head_lemma == head_lemma,
        PrecisionGroup.status == "approved",
        PrecisionGroup.kind == "precision",
    )
    return [GroupRef(id=g.id, sense_gloss=g.sense_gloss) for g in session.scalars(stmt)]


def _suggestion_events_stmt(
    user_id: str,
    start: datetime,
    end: datetime,
    event_type: str,
    *,
    prompt_version: int | None = None,
    model: str | None = None,
) -> Select[tuple[Event]]:
    stmt = select(Event).where(
        Event.user_id == user_id,
        Event.type == event_type,
        Event.created_at >= start,
        Event.created_at < end,
    )
    if prompt_version is None and model is None:
        return stmt
    stmt = (
        stmt.join(Suggestion, Suggestion.id == Event.subject_id)
        .join(EditorRun, EditorRun.id == Suggestion.editor_run_id)
        .join(LlmCall, LlmCall.id == EditorRun.llm_call_id)
        .where(Suggestion.user_id == user_id, EditorRun.user_id == user_id)
    )
    if prompt_version is not None:
        stmt = stmt.where(LlmCall.prompt_version == prompt_version)
    if model is not None:
        stmt = stmt.where(LlmCall.model == model)
    return stmt


def acceptance_rate(
    session: Session,
    user_id: str,
    start: datetime,
    end: datetime,
    *,
    prompt_version: int | None = None,
    model: str | None = None,
) -> float | None:
    shown = len(
        list(
            session.scalars(
                _suggestion_events_stmt(
                    user_id,
                    start,
                    end,
                    "suggestion_shown",
                    prompt_version=prompt_version,
                    model=model,
                )
            )
        )
    )
    if shown == 0:
        return None
    accepted = len(
        list(
            session.scalars(
                _suggestion_events_stmt(
                    user_id,
                    start,
                    end,
                    "suggestion_accepted",
                    prompt_version=prompt_version,
                    model=model,
                )
            )
        )
    )
    return accepted / shown


def spontaneous_correct_use(
    session: Session, user_id: str, start: datetime, end: datetime
) -> float | None:
    """Share of accepts that later see an unprompted correct use within 30 days."""
    accepts = list(
        session.scalars(
            select(Event).where(
                Event.user_id == user_id,
                Event.type == "suggestion_accepted",
                Event.created_at >= start,
                Event.created_at < end,
            )
        )
    )
    if not accepts:
        return None
    successes = 0
    for accept in accepts:
        option_id = (accept.payload or {}).get("option_id")
        if not option_id:
            continue
        window_end = accept.created_at + timedelta(days=30)
        used = session.scalars(
            select(Event).where(
                Event.user_id == user_id,
                Event.type == "word_used",
                Event.created_at >= accept.created_at,
                Event.created_at <= window_end,
            )
        )
        if any(
            (e.payload or {}).get("option_id") == option_id
            and (e.payload or {}).get("correct") is True
            and (e.payload or {}).get("prompted") is False
            for e in used
        ):
            successes += 1
    return successes / len(accepts)


def _idiom_option_ids(session: Session, option_ids: set[str]) -> set[str]:
    """Return the subset of option_ids that belong to idiom groups."""
    if not option_ids:
        return set()
    rows = session.execute(
        select(PrecisionOption.id)
        .join(PrecisionGroup, PrecisionGroup.id == PrecisionOption.group_id)
        .where(
            PrecisionOption.id.in_(option_ids),
            PrecisionGroup.kind == "idiom",
        )
    ).all()
    return {row[0] for row in rows}


def _word_used_events(
    session: Session, user_id: str, start: datetime, end: datetime
) -> list[Event]:
    return list(
        session.scalars(
            select(Event).where(
                Event.user_id == user_id,
                Event.type == "word_used",
                Event.created_at >= start,
                Event.created_at < end,
            )
        )
    )


def misuse_rate(session: Session, user_id: str, start: datetime, end: datetime) -> float | None:
    """Misuse among non-idiom word_used events; idioms have their own rate."""
    events = _word_used_events(session, user_id, start, end)
    option_ids = {
        oid
        for e in events
        if (oid := (e.payload or {}).get("option_id")) and isinstance(oid, str)
    }
    idiom_ids = _idiom_option_ids(session, option_ids)
    non_idiom = [
        e
        for e in events
        if (e.payload or {}).get("option_id") not in idiom_ids
    ]
    if not non_idiom:
        return None
    wrong = sum(1 for e in non_idiom if (e.payload or {}).get("correct") is False)
    return wrong / len(non_idiom)


def idiom_misuse_rate(
    session: Session, user_id: str, start: datetime, end: datetime
) -> float | None:
    """Misuse among idiom word_used events only."""
    events = _word_used_events(session, user_id, start, end)
    option_ids = {
        oid
        for e in events
        if (oid := (e.payload or {}).get("option_id")) and isinstance(oid, str)
    }
    idiom_ids = _idiom_option_ids(session, option_ids)
    idiom_events = [
        e for e in events if (e.payload or {}).get("option_id") in idiom_ids
    ]
    if not idiom_events:
        return None
    wrong = sum(1 for e in idiom_events if (e.payload or {}).get("correct") is False)
    return wrong / len(idiom_events)


def drill_score_weekly(
    session: Session, user_id: str, start: datetime, end: datetime
) -> list[WeekScore]:
    rows: list[WeekScore] = []
    for week_end in _week_ends(start, end):
        week_start = max(week_end - timedelta(days=7), start)
        scores = list(
            session.scalars(
                select(DrillAttempt.score).where(
                    DrillAttempt.user_id == user_id,
                    DrillAttempt.created_at >= week_start,
                    DrillAttempt.created_at < week_end,
                )
            )
        )
        mean = sum(scores) / len(scores) if scores else None
        rows.append(WeekScore(label=week_end.date().isoformat(), end=week_end, score=mean))
    return rows


def lexical_diversity(
    session: Session, user_id: str, start: datetime, end: datetime
) -> float | None:
    """MTLD over alphabetic tokens in user messages; None below 100 words."""
    messages = _user_messages(session, user_id, start, end)
    tokens: list[str] = []
    for message in messages:
        tokens.extend(t.lower() for t in _WORD_RE.findall(message.content))
    return mtld(tokens)


def lemma_detail(
    session: Session, user_id: str, start: datetime, end: datetime, lemma: str
) -> LemmaDetail:
    """Per-crutch-lemma weekly rate plus learned options and their use counts."""
    lemma = lemma.lower()
    weekly = [
        WeekRate(
            label=week_end.date().isoformat(),
            end=week_end,
            rate=crutch_rate_for_lemma(
                session,
                user_id,
                max(week_end - timedelta(days=7), start),
                week_end,
                lemma,
            ),
        )
        for week_end in _week_ends(start, end)
    ]
    group_ids = list(
        session.scalars(
            select(PrecisionGroup.id).where(
                PrecisionGroup.head_lemma == lemma,
                PrecisionGroup.status == "approved",
                PrecisionGroup.kind == "precision",
            )
        )
    )
    options: list[OptionUsage] = []
    if group_ids:
        opts = list(
            session.scalars(
                select(PrecisionOption).where(
                    PrecisionOption.group_id.in_(group_ids),
                    PrecisionOption.status == "approved",
                )
            )
        )
        accepts = {
            (e.payload or {}).get("option_id")
            for e in session.scalars(
                select(Event).where(
                    Event.user_id == user_id,
                    Event.type == "suggestion_accepted",
                    Event.created_at >= start,
                    Event.created_at < end,
                )
            )
        }
        for opt in opts:
            if opt.id not in accepts:
                continue
            uses = list(
                session.scalars(
                    select(Event).where(
                        Event.user_id == user_id,
                        Event.type == "word_used",
                        Event.created_at >= start,
                        Event.created_at < end,
                    )
                )
            )
            matched = [e for e in uses if (e.payload or {}).get("option_id") == opt.id]
            options.append(
                OptionUsage(
                    option_id=opt.id,
                    word=opt.word,
                    uses=len(matched),
                    correct_uses=sum(
                        1 for e in matched if (e.payload or {}).get("correct") is True
                    ),
                )
            )
    return LemmaDetail(lemma=lemma, weekly=weekly, options=options)


def default_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Last twelve weeks ending at `now` (UTC)."""
    end = now or datetime.now(UTC)
    start = end - timedelta(weeks=12)
    return start, end
