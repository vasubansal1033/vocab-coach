"""Choose-the-word grading, API prompt-only responses, and FakeLLM create."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.events import Event
from vocab.exercises.grading import grade_choice
from vocab.exercises.schemas import (
    ChoiceAnswer,
    ChoiceAnswerCandidate,
    ChoiceResponse,
)
from vocab.exercises.service import answer_exercise, create_choice
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.practice.models import SrsCard
from vocab.practice.srs import ensure_card


def _prefer_fix_repair(session: Session, user_id: str) -> None:
    """Make select_group return fix.repair for FakeLLM fixtures that use its IDs."""
    ensure_card(session, user_id=user_id, option_id="fix.repair/resolve")
    card = session.scalars(
        select(SrsCard).where(
            SrsCard.user_id == user_id, SrsCard.option_id == "fix.repair/resolve"
        )
    ).one()
    card.due_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    load_seeds(session)


CHOICE_SETTINGS = Settings(
    _env_file=None,
    session_secret="test",
    llm_choice_gen_model="fake-choice",
    llm_choice_gen_prompt_version=1,
)


def _sample_answer() -> ChoiceAnswer:
    return ChoiceAnswer(
        best_option_id="fix.repair/resolve",
        candidates=[
            ChoiceAnswerCandidate(
                option_id="fix.repair/resolve",
                fit="fits",
                reason="Removes the cause.",
                best=True,
            ),
            ChoiceAnswerCandidate(
                option_id="fix.repair/patch",
                fit="partly",
                reason="Could work as a temporary change.",
                best=False,
            ),
            ChoiceAnswerCandidate(
                option_id="fix.repair/work around",
                fit="wrong",
                reason="Leaves the cause in place.",
                best=False,
            ),
            ChoiceAnswerCandidate(
                option_id="fix.repair/mitigate",
                fit="wrong",
                reason="Only reduces harm.",
                best=False,
            ),
        ],
    )


def test_grade_choice_correct_best() -> None:
    result = grade_choice(
        _sample_answer(),
        ChoiceResponse(
            best_option_id="fix.repair/resolve",
            marked_option_ids=["fix.repair/resolve"],
        ),
    )
    assert result.correct is True
    assert result.feedback.best_option_id == "fix.repair/resolve"


def test_grade_choice_wrong_best() -> None:
    result = grade_choice(
        _sample_answer(),
        ChoiceResponse(
            best_option_id="fix.repair/patch",
            marked_option_ids=["fix.repair/patch"],
        ),
    )
    assert result.correct is False


def test_grade_choice_correct_best_with_extra_mark() -> None:
    result = grade_choice(
        _sample_answer(),
        ChoiceResponse(
            best_option_id="fix.repair/resolve",
            marked_option_ids=["fix.repair/resolve", "fix.repair/mitigate"],
        ),
    )
    assert result.correct is True
    by_id = {c.option_id: c for c in result.feedback.candidates}
    assert by_id["fix.repair/mitigate"].user_marked is True
    assert by_id["fix.repair/mitigate"].best is False


@pytest.mark.asyncio
async def test_create_and_answer_choice(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    gen = {
        "situation": "A flaky nightly job keeps failing for the same root cause.",
        "sentence": "We need to ___ the timeout before the next release.",
        "candidates": [
            {
                "option_id": "fix.repair/resolve",
                "fit": "fits",
                "reason": "Removes the cause so it will not return.",
                "best": True,
            },
            {
                "option_id": "fix.repair/patch",
                "fit": "partly",
                "reason": "A quick change might help but may not last.",
                "best": False,
            },
            {
                "option_id": "fix.repair/work around",
                "fit": "wrong",
                "reason": "Avoids the issue without fixing it.",
                "best": False,
            },
            {
                "option_id": "fix.repair/mitigate",
                "fit": "wrong",
                "reason": "Only reduces the harm.",
                "best": False,
            },
        ],
    }
    use_fake(FakeLLM(fixtures={"choice_gen": json.dumps(gen)}))
    _prefer_fix_repair(session, user.id)

    exercise = await create_choice(session, user_id=user.id, settings=CHOICE_SETTINGS)
    assert exercise.item_type == "choice"
    assert "___" in exercise.prompt["sentence"]
    assert "answer" in exercise.__dict__ or exercise.answer

    attempt = answer_exercise(
        session,
        exercise=exercise,
        user_id=user.id,
        response=ChoiceResponse(
            best_option_id="fix.repair/resolve",
            marked_option_ids=["fix.repair/resolve", "fix.repair/patch"],
        ),
    )
    assert attempt.correct is True
    event = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "exercise_answered")
    ).one()
    assert event.payload["correct"] is True
    assert event.payload["item_type"] == "choice"
    reviewed = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
    ).all()
    assert any(e.payload.get("source") == "exercise" for e in reviewed)


@pytest.mark.asyncio
async def test_get_exercise_never_includes_answer(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
    seeded: None,
) -> None:
    user = make_user()
    login_as(user)
    gen = {
        "situation": "A flaky nightly job keeps failing for the same root cause.",
        "sentence": "We need to ___ the timeout before the next release.",
        "candidates": [
            {
                "option_id": "fix.repair/resolve",
                "fit": "fits",
                "reason": "Removes the cause.",
                "best": True,
            },
            {
                "option_id": "fix.repair/patch",
                "fit": "partly",
                "reason": "Temporary.",
                "best": False,
            },
            {
                "option_id": "fix.repair/work around",
                "fit": "wrong",
                "reason": "Avoids only.",
                "best": False,
            },
            {
                "option_id": "fix.repair/mitigate",
                "fit": "wrong",
                "reason": "Reduces harm.",
                "best": False,
            },
        ],
    }
    use_fake(FakeLLM(fixtures={"choice_gen": json.dumps(gen)}))
    _prefer_fix_repair(session, user.id)
    exercise = await create_choice(session, user_id=user.id, settings=CHOICE_SETTINGS)
    response = client.get(f"/api/exercises/{exercise.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == exercise.id
    assert "answer" not in body
    assert "prompt" in body
    assert body["prompt"]["sentence"].count("___") == 1
    raw = response.text
    assert "Removes the cause" not in raw
    assert '"fit"' not in raw
    assert '"answer"' not in raw


@pytest.mark.llm
@pytest.mark.asyncio
async def test_choice_gen_real_model(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    """Calls the configured choice_gen model; skipped unless RUN_LLM_TESTS=1."""
    user = make_user()
    exercise = await create_choice(session, user_id=user.id)
    assert exercise.item_type == "choice"
    assert exercise.prompt["sentence"].count("___") == 1
    assert 4 <= len(exercise.prompt["candidates"]) <= 6
    answer = ChoiceAnswer.model_validate(exercise.answer)
    assert sum(1 for c in answer.candidates if c.best) == 1
