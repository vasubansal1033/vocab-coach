"""Compare grading, create_compare, card API, and attempt smoke tests."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from lexicon_fixture import seed_lexicon
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.events import Event
from vocab.exercises.grading import (
    grade_compare_misuse,
    grade_compare_order,
    grade_compare_pair,
)
from vocab.exercises.schemas import (
    CompareMisuseAnswer,
    CompareMisuseResponse,
    CompareOrderAnswer,
    CompareOrderResponse,
    ComparePairAnswer,
    ComparePairResponse,
)
from vocab.exercises.service import answer_exercise, create_compare
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.practice.srs import ensure_card


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    seed_lexicon(session)


COMPARE_SETTINGS = Settings(
    _env_file=None,
    session_secret="test",
    llm_compare_gen_model="fake-compare",
    llm_compare_gen_prompt_version=1,
)


def test_grade_compare_pair_correct() -> None:
    answer = ComparePairAnswer(
        fits_option_ids=[
            "confusable.imply-infer/imply",
            "confusable.imply-infer/infer",
        ]
    )
    result = grade_compare_pair(
        answer,
        ComparePairResponse(
            fits_option_ids=[
                "confusable.imply-infer/imply",
                "confusable.imply-infer/infer",
            ]
        ),
    )
    assert result.correct is True


def test_grade_compare_pair_wrong() -> None:
    answer = ComparePairAnswer(
        fits_option_ids=[
            "confusable.imply-infer/imply",
            "confusable.imply-infer/infer",
        ]
    )
    result = grade_compare_pair(
        answer,
        ComparePairResponse(
            fits_option_ids=[
                "confusable.imply-infer/infer",
                "confusable.imply-infer/imply",
            ]
        ),
    )
    assert result.correct is False


def test_grade_compare_misuse_correct() -> None:
    answer = CompareMisuseAnswer(
        misused_option_id="confusable.imply-infer/infer",
        replacement_option_id="confusable.imply-infer/imply",
        reason="The speaker suggests; the listener infers.",
    )
    result = grade_compare_misuse(
        answer,
        CompareMisuseResponse(
            misused_option_id="confusable.imply-infer/infer",
            replacement_option_id="confusable.imply-infer/imply",
        ),
    )
    assert result.correct is True
    assert "listener" in result.feedback.reason


def test_grade_compare_misuse_wrong_replacement() -> None:
    answer = CompareMisuseAnswer(
        misused_option_id="confusable.imply-infer/infer",
        replacement_option_id="confusable.imply-infer/imply",
        reason="Swap them.",
    )
    result = grade_compare_misuse(
        answer,
        CompareMisuseResponse(
            misused_option_id="confusable.imply-infer/infer",
            replacement_option_id="confusable.imply-infer/infer",
        ),
    )
    assert result.correct is False


def test_grade_compare_order_correct() -> None:
    answer = CompareOrderAnswer(
        ordered_option_ids=[
            "confusable.annoyed-irritated-exasperated-livid/annoyed",
            "confusable.annoyed-irritated-exasperated-livid/irritated",
            "confusable.annoyed-irritated-exasperated-livid/exasperated",
            "confusable.annoyed-irritated-exasperated-livid/livid",
        ]
    )
    result = grade_compare_order(
        answer,
        CompareOrderResponse(ordered_option_ids=list(answer.ordered_option_ids)),
    )
    assert result.correct is True


def test_grade_compare_order_wrong() -> None:
    answer = CompareOrderAnswer(
        ordered_option_ids=[
            "confusable.annoyed-irritated-exasperated-livid/annoyed",
            "confusable.annoyed-irritated-exasperated-livid/irritated",
            "confusable.annoyed-irritated-exasperated-livid/exasperated",
            "confusable.annoyed-irritated-exasperated-livid/livid",
        ]
    )
    wrong = list(reversed(answer.ordered_option_ids))
    result = grade_compare_order(answer, CompareOrderResponse(ordered_option_ids=wrong))
    assert result.correct is False


@pytest.mark.asyncio
async def test_create_compare_order_and_answer(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    group_id = "confusable.annoyed-irritated-exasperated-livid"
    ensure_card(
        session,
        user_id=user.id,
        option_id=f"{group_id}/annoyed",
    )
    exercise = await create_compare(
        session,
        user_id=user.id,
        group_id=group_id,
        item_type="compare_order",
        settings=COMPARE_SETTINGS,
    )
    assert exercise.item_type == "compare_order"
    assert exercise.llm_call_id is None
    answer = CompareOrderAnswer.model_validate(exercise.answer)
    attempt = answer_exercise(
        session,
        exercise=exercise,
        user_id=user.id,
        response=CompareOrderResponse(ordered_option_ids=list(answer.ordered_option_ids)),
    )
    assert attempt.correct is True
    event = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "exercise_answered")
    ).one()
    assert event.payload["item_type"] == "compare_order"
    assert event.payload["correct"] is True
    reviewed = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
    ).all()
    assert any(e.payload.get("source") == "exercise" for e in reviewed)


@pytest.mark.asyncio
async def test_create_compare_pair_with_fake_llm(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    gen = {
        "sentences": [
            {
                "text": "Her email seemed to ___ that the launch slipped.",
                "fits_option_id": "confusable.imply-infer/imply",
            },
            {
                "text": "From the missing metrics we ___ the exporter had stalled.",
                "fits_option_id": "confusable.imply-infer/infer",
            },
        ]
    }
    use_fake(FakeLLM(fixtures={"compare_gen": json.dumps(gen)}))
    exercise = await create_compare(
        session,
        user_id=user.id,
        group_id="confusable.imply-infer",
        item_type="compare_pair",
        settings=COMPARE_SETTINGS,
    )
    assert exercise.item_type == "compare_pair"
    assert len(exercise.prompt["sentences"]) == 2
    assert "answer" not in exercise.prompt


def test_compare_api_list_and_card_smoke(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
    seeded: None,
) -> None:
    user = make_user()
    login_as(user)
    listed = client.get("/api/compare")
    assert listed.status_code == 200
    rows = listed.json()
    assert any(r["id"] == "confusable.imply-infer" for r in rows)
    annoyed = next(r for r in rows if r["id"].endswith("annoyed-irritated-exasperated-livid"))
    assert annoyed["has_strength_order"] is True

    card = client.get("/api/compare/confusable.imply-infer")
    assert card.status_code == 200
    body = card.json()
    assert body["sense_gloss"]
    assert len(body["options"]) == 2
    assert all(opt["distinction"] and opt["example"] for opt in body["options"])
    assert all("collocations" in opt for opt in body["options"])


def test_compare_order_exercise_api_smoke(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
    seeded: None,
) -> None:
    user = make_user()
    login_as(user)
    group_id = "confusable.annoyed-irritated-exasperated-livid"
    created = client.post(
        "/api/exercises/compare",
        json={"group_id": group_id, "item_type": "compare_order"},
    )
    assert created.status_code == 200
    exercise = created.json()
    assert exercise["item_type"] == "compare_order"
    assert "answer" not in exercise
    assert "options" in exercise["prompt"]

    got = client.get(f"/api/exercises/{exercise['id']}")
    assert got.status_code == 200
    assert "answer" not in got.json()
    assert "ordered_option_ids" not in got.text

    # Pull the stored answer only through the DB for the correct submit.
    from vocab.exercises.models import Exercise

    row = session.get(Exercise, exercise["id"])
    assert row is not None
    ordered = list(row.answer["ordered_option_ids"])
    attempt = client.post(
        f"/api/exercises/{exercise['id']}/attempt",
        json={"ordered_option_ids": ordered},
    )
    assert attempt.status_code == 200
    assert attempt.json()["correct"] is True


@pytest.mark.llm
@pytest.mark.asyncio
async def test_compare_gen_real_model(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    """Calls the configured compare_gen model; skipped unless RUN_LLM_TESTS=1."""
    user = make_user()
    exercise = await create_compare(
        session,
        user_id=user.id,
        group_id="confusable.imply-infer",
        item_type="compare_pair",
    )
    assert exercise.item_type == "compare_pair"
    assert len(exercise.prompt["sentences"]) == 2
    for sentence in exercise.prompt["sentences"]:
        assert sentence.count("___") == 1
