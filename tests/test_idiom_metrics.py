"""Idiom misuse is separate from general misuse_rate."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from lexicon_fixture import seed_lexicon
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.events import Event, WordUsedPayload, record_event
from vocab.metrics.queries import idiom_misuse_rate, misuse_rate


def test_misuse_rate_excludes_idioms(
    session: Session, make_user: Callable[..., User]
) -> None:
    seed_lexicon(session)
    user = make_user()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=7)
    # Two non-idiom uses: one wrong. One idiom use wrong. Misuse should be 1/2.
    cases = [
        ("fix.repair/resolve", True, 1),
        ("fix.repair/patch", False, 2),
        ("idiom.agree/on the same page", False, 3),
    ]
    for option_id, correct, minutes in cases:
        record_event(
            session,
            user_id=user.id,
            type="word_used",
            subject_type="message",
            subject_id=f"msg-{minutes}",
            payload=WordUsedPayload(
                option_id=option_id,
                correct=correct,
                prompted=False,
                judge_call_id=None,
            ),
        )
        row = session.scalars(
            select(Event).where(
                Event.user_id == user.id,
                Event.subject_id == f"msg-{minutes}",
            )
        ).one()
        row.created_at = start + timedelta(minutes=minutes)
    session.commit()

    assert abs(misuse_rate(session, user.id, start, end) - 0.5) < 1e-12
    assert abs(idiom_misuse_rate(session, user.id, start, end) - 1.0) < 1e-12
