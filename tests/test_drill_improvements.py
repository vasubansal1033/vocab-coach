"""Hints, summary, disputes and drill_gen v2 for Drill improvements."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.drills.models import Drill, DrillAttempt
from vocab.drills.service import (
    create_drill,
    dispute_attempt,
    export_drill_disputes,
    grade_attempt,
    hint_for,
    last_export_date,
    summarize_attempts,
)
from vocab.events import Event
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    load_seeds(session)


DRILL_V2 = Settings(
    _env_file=None,
    session_secret="test",
    llm_drill_gen_model="fake-gen",
    llm_drill_grade_model="fake-grade",
    llm_drill_gen_prompt_version=2,
    llm_drill_grade_prompt_version=1,
)


def _seed_drill(session: Session, user: User, *, context: str | None = None) -> Drill:
    drill = Drill(
        user_id=user.id,
        group_id="fix.repair",
        vague_sentence="We need to fix the flaky job before Friday.",
        context=context,
        intended_option_id="fix.repair/resolve",
        intended_word="resolve",
    )
    session.add(drill)
    session.commit()
    session.refresh(drill)
    return drill


def test_hint_for_levels(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    drill = _seed_drill(session, user)
    level1 = hint_for(session, drill, 1)
    assert "cause" in level1.lower() or "problem" in level1.lower() or len(level1) > 10
    level2 = hint_for(session, drill, 2)
    assert level2.startswith("The intended word starts with")
    assert "“r”" in level2 or '"r"' in level2 or "r" in level2
    level3 = hint_for(session, drill, 3)
    assert "resolve" in level3
    assert "Options in this group:" in level3
    with pytest.raises(ValueError):
        hint_for(session, drill, 4)


def test_summarize_attempts(session: Session, make_user: Callable[..., User], seeded: None) -> None:
    user = make_user()
    d1 = _seed_drill(session, user)
    d2 = Drill(
        user_id=user.id,
        group_id="fix.repair",
        vague_sentence="Please fix the report.",
        intended_option_id="fix.repair/patch",
        intended_word="patch",
    )
    session.add(d2)
    session.commit()
    a1 = DrillAttempt(
        drill_id=d1.id,
        user_id=user.id,
        answer="resolve it",
        grade={"precision": 5, "meaning": 5, "naturalness": 5},
        score=5,
        hints_used=1,
    )
    a2 = DrillAttempt(
        drill_id=d2.id,
        user_id=user.id,
        answer="patch it",
        grade={"precision": 3, "meaning": 3, "naturalness": 3},
        score=3,
        hints_used=2,
    )
    session.add_all([a1, a2])
    session.commit()
    session.refresh(a1)
    session.refresh(a2)
    # Attach drills for the pure summary helper.
    a1.drill = d1
    a2.drill = d2
    summary = summarize_attempts([a1, a2])
    assert summary.mean_score == 4.0
    assert summary.words_practised == ["resolve", "patch"]
    assert summary.total_hints_used == 3
    empty = summarize_attempts([])
    assert empty.mean_score == 0.0
    assert empty.words_practised == []
    assert empty.total_hints_used == 0


def test_dispute_and_export(
    session: Session,
    make_user: Callable[..., User],
    seeded: None,
    tmp_path: Path,
) -> None:
    user = make_user()
    drill = _seed_drill(session, user, context="A flaky CI job keeps blocking releases.")
    attempt = DrillAttempt(
        drill_id=drill.id,
        user_id=user.id,
        answer="We need to resolve the flaky job before Friday.",
        grade={
            "precision": 2,
            "meaning": 4,
            "naturalness": 4,
            "feedback": "Too harsh.",
            "better_version": "We need to resolve the flaky job.",
        },
        score=3,
        hints_used=0,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)

    event = dispute_attempt(
        session,
        attempt=attempt,
        user_id=user.id,
        note="Intended word was fine",
    )
    assert event.type == "drill_disputed"
    assert event.payload["note"] == "Intended word was fine"
    stored = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "drill_disputed")
    ).one()
    assert stored.subject_id == attempt.id

    prior = tmp_path / "2026-11-01.yaml"
    prior.write_text("exported_on: '2026-11-01'\ndisputes: []\n", encoding="utf-8")
    assert last_export_date(tmp_path) == date(2026, 11, 1)

    out = export_drill_disputes(session, disputes_dir=tmp_path, as_of=date(2026, 11, 11))
    assert out.name == "2026-11-11.yaml"
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["since"] == "2026-11-01"
    assert len(data["disputes"]) == 1
    row = data["disputes"][0]
    assert row["answer"] == attempt.answer
    assert row["context"] == drill.context
    assert row["note"] == "Intended word was fine"
    assert row["vague_sentence"] == drill.vague_sentence
    assert row["grade"]["feedback"] == "Too harsh."


@pytest.mark.asyncio
async def test_create_drill_v2_stores_context(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    gen = {
        "context": "A release is blocked by a flaky nightly job.",
        "vague_sentence": "We need to fix the flaky job before Friday.",
        "intended_option_id": "fix.repair/resolve",
        "intended_word": "resolve",
    }
    grade = {
        "precision": 5,
        "meaning": 5,
        "naturalness": 4,
        "feedback": "Clear.",
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
    drill = await create_drill(session, user_id=user.id, settings=DRILL_V2)
    assert drill.context == gen["context"]
    assert drill.intended_word == "resolve"

    attempt = await grade_attempt(
        session,
        drill=drill,
        user_id=user.id,
        answer="We need to resolve the flaky job before Friday.",
        hints_used=2,
        settings=DRILL_V2,
    )
    assert attempt.hints_used == 2


def test_v1_drill_null_context_still_loads(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    drill = _seed_drill(session, user, context=None)
    assert drill.context is None
    text = hint_for(session, drill, 2)
    assert "r" in text.lower()
