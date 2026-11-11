"""Create and review FSRS cards; select due words; rebuild from events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fsrs import Card, Rating, Scheduler
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vocab.events import CardReviewedPayload, Event, record_event
from vocab.lexicon.models import PrecisionOption
from vocab.practice.models import SrsCard, utcnow

Source = Literal["conversation", "drill", "review_page", "exercise"]

_RATING_MAP = {
    "Again": Rating.Again,
    "Hard": Rating.Hard,
    "Good": Rating.Good,
    "Easy": Rating.Easy,
}


def _parse_due(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _scheduler() -> Scheduler:
    return Scheduler()


def ensure_card(session: Session, *, user_id: str, option_id: str) -> SrsCard:
    """Create an FSRS card for an accepted option if the user does not have one."""
    existing = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user_id, SrsCard.option_id == option_id)
    ).first()
    if existing is not None:
        return existing
    card = Card()
    data = card.to_dict()
    row = SrsCard(
        user_id=user_id,
        option_id=option_id,
        fsrs_card=data,
        due_at=_parse_due(data["due"]),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def review_card(
    session: Session,
    *,
    user_id: str,
    option_id: str,
    rating: str,
    source: Source,
) -> SrsCard:
    """Apply an FSRS rating and record card_reviewed."""
    if rating not in _RATING_MAP:
        raise ValueError(f"unknown rating: {rating}")
    row = ensure_card(session, user_id=user_id, option_id=option_id)
    card = Card.from_dict(row.fsrs_card)
    updated, _log = _scheduler().review_card(card, _RATING_MAP[rating])
    data = updated.to_dict()
    row.fsrs_card = data
    row.due_at = _parse_due(data["due"])
    record_event(
        session,
        user_id=user_id,
        type="card_reviewed",
        subject_type="srs_card",
        subject_id=row.id,
        payload=CardReviewedPayload(rating=rating, source=source, option_id=option_id),
    )
    session.commit()
    session.refresh(row)
    return row


def due_options(session: Session, user_id: str, *, limit: int = 3) -> list[PrecisionOption]:
    """Up to `limit` overdue options, most overdue first."""
    now = utcnow()
    rows = session.scalars(
        select(SrsCard)
        .where(SrsCard.user_id == user_id, SrsCard.due_at <= now)
        .order_by(SrsCard.due_at.asc())
        .limit(limit)
    ).all()
    options: list[PrecisionOption] = []
    for row in rows:
        opt = session.get(PrecisionOption, row.option_id)
        if opt is not None:
            options.append(opt)
    return options


def due_words(session: Session, user_id: str, *, limit: int = 3) -> list[str]:
    """Surface words for the partner prompt."""
    return [opt.word for opt in due_options(session, user_id, limit=limit)]


def learned_option_rows(session: Session, user_id: str) -> list[PrecisionOption]:
    """All options the user has a card for (learned set)."""
    rows = session.scalars(select(SrsCard).where(SrsCard.user_id == user_id)).all()
    options: list[PrecisionOption] = []
    for row in rows:
        opt = session.get(PrecisionOption, row.option_id)
        if opt is not None:
            options.append(opt)
    return options


def rebuild_cards(session: Session, user_id: str) -> list[SrsCard]:
    """Replay card_reviewed events into srs_cards for one user."""
    session.execute(delete(SrsCard).where(SrsCard.user_id == user_id))
    session.commit()

    events = session.scalars(
        select(Event)
        .where(Event.user_id == user_id, Event.type == "card_reviewed")
        .order_by(Event.created_at.asc())
    ).all()

    by_option: dict[str, list[str]] = {}
    for event in events:
        option_id = event.payload.get("option_id")
        rating = event.payload.get("rating")
        if not option_id or not rating:
            continue
        by_option.setdefault(str(option_id), []).append(str(rating))

    rebuilt: list[SrsCard] = []
    for option_id, ratings in by_option.items():
        card = Card()
        for rating in ratings:
            card, _ = _scheduler().review_card(card, _RATING_MAP[rating])
        data = card.to_dict()
        row = SrsCard(
            user_id=user_id,
            option_id=option_id,
            fsrs_card=data,
            due_at=_parse_due(data["due"]),
        )
        session.add(row)
        rebuilt.append(row)
    session.commit()
    for row in rebuilt:
        session.refresh(row)
    return rebuilt
