"""Drill selector and gen/grade with FakeLLM."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from lexicon_fixture import seed_lexicon
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.drills.select import select_group
from vocab.drills.service import create_drill, grade_attempt
from vocab.events import Event
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.practice.models import SrsCard
from vocab.practice.srs import ensure_card


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    seed_lexicon(session)


DRILL_SETTINGS = Settings(
    _env_file=None,
    session_secret="test",
    llm_drill_gen_model="fake-gen",
    llm_drill_grade_model="fake-grade",
    llm_drill_gen_prompt_version=1,
    llm_drill_grade_prompt_version=1,
)


def test_selector_prefers_due_card_group(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    ensure_card(session, user_id=user.id, option_id="fix.repair/resolve")
    card = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user.id, SrsCard.option_id == "fix.repair/resolve")
    ).one()
    card.due_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()

    group = select_group(session, user.id)
    assert group.id == "fix.repair"


@pytest.mark.asyncio
async def test_create_and_grade_drill(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    gen = {
        "vague_sentence": "We need to fix the flaky job before Friday.",
        "intended_option_id": "fix.repair/resolve",
        "intended_word": "resolve",
    }
    grade = {
        "precision": 5,
        "meaning": 5,
        "naturalness": 4,
        "feedback": "Clear and precise.",
        "better_version": None,
        "used_option_id": "fix.repair/resolve",
    }
    use_fake(
        FakeLLM(
            fixtures={
                "drill_gen": json.dumps(gen),
                "drill_grade": json.dumps(grade),
            }
        )
    )
    ensure_card(session, user_id=user.id, option_id="fix.repair/resolve")

    drill = await create_drill(session, user_id=user.id, settings=DRILL_SETTINGS)
    assert "fix" in drill.vague_sentence.lower() or "flaky" in drill.vague_sentence.lower()
    assert drill.intended_word == "resolve"

    attempt = await grade_attempt(
        session,
        drill=drill,
        user_id=user.id,
        answer="We need to resolve the flaky job before Friday.",
        settings=DRILL_SETTINGS,
    )
    assert attempt.score == 5
    event = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "drill_graded")
    ).one()
    assert event.payload["score"] == 5
    reviewed = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
    ).all()
    assert any(e.payload.get("source") == "drill" for e in reviewed)
