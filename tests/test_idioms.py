"""Idiom editor filter, grading, write step, and API smoke tests."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.models import Conversation, Message
from vocab.editor.models import EditorRun, Suggestion
from vocab.editor.service import build_editor_variables, conversation_has_idiom_suggestion
from vocab.events import Event, SuggestionShownPayload, record_event
from vocab.exercises.grading import grade_idiom_select
from vocab.exercises.schemas import IdiomSelectAnswer, IdiomSelectResponse, IdiomWriteResponse
from vocab.exercises.service import answer_exercise, answer_idiom_write, create_idiom
from vocab.lexicon.models import PrecisionGroup
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.nlp.analyzer import analyze
from vocab.nlp.types import CandidateSpan


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    load_seeds(session)


IDIOM_SETTINGS = Settings(
    _env_file=None,
    session_secret="test",
    llm_compare_gen_model="fake-compare",
    llm_compare_gen_prompt_version=2,
    llm_usage_judge_model="fake-judge",
    llm_usage_judge_prompt_version=1,
)


def test_grade_idiom_select_correct_and_wrong() -> None:
    answer = IdiomSelectAnswer(
        correct_id="idiom.agree/on the same page",
        option_id="idiom.agree/on the same page",
    )
    ok = grade_idiom_select(
        answer,
        IdiomSelectResponse(selected_id="idiom.agree/on the same page"),
    )
    assert ok.correct is True
    bad = grade_idiom_select(
        answer,
        IdiomSelectResponse(selected_id="distract:0"),
    )
    assert bad.correct is False


@pytest.mark.asyncio
async def test_editor_excludes_idioms_when_allow_idioms_false(
    session: Session, seeded: None
) -> None:
    message = "We agree on the timeline."
    analysis = analyze(message)
    analysis.candidates = [
        CandidateSpan(
            text="agree",
            start=3,
            end=8,
            lemma="agree",
            pos="VERB",
            reason="crutch",
        )
    ]
    variables = await build_editor_variables(
        session,
        message=message,
        analysis=analysis,
        allow_idioms=False,
        conversation_id="conv-1",
        user_id="user-1",
    )
    assert "idiom.agree" not in {g["id"] for g in variables["groups"]}


@pytest.mark.asyncio
async def test_editor_includes_idioms_when_allowed(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    conversation = Conversation(
        user_id=user.id,
        title="Team chat",
        allow_idioms=True,
    )
    session.add(conversation)
    session.commit()
    message = "We agree on the timeline."
    analysis = analyze(message)
    analysis.candidates = [
        CandidateSpan(
            text="agree",
            start=3,
            end=8,
            lemma="agree",
            pos="VERB",
            reason="crutch",
        )
    ]
    variables = await build_editor_variables(
        session,
        message=message,
        analysis=analysis,
        allow_idioms=True,
        conversation_id=conversation.id,
        user_id=user.id,
    )
    assert "idiom.agree" in {g["id"] for g in variables["groups"]}


@pytest.mark.asyncio
async def test_editor_excludes_idioms_after_one_shown(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    conversation = Conversation(
        user_id=user.id,
        title="Team chat",
        allow_idioms=True,
    )
    session.add(conversation)
    session.flush()
    msg = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        role="user",
        content="We agree.",
        word_count=2,
    )
    session.add(msg)
    session.flush()
    run = EditorRun(
        message_id=msg.id,
        user_id=user.id,
        llm_call_id=None,
        output={"overview": "", "suggestions": [], "keep": []},
    )
    session.add(run)
    session.flush()
    suggestion = Suggestion(
        editor_run_id=run.id,
        message_id=msg.id,
        user_id=user.id,
        original_text="agree",
        span_start=3,
        span_end=8,
        group_id="idiom.agree",
        question=None,
        rank=0,
    )
    session.add(suggestion)
    session.flush()
    record_event(
        session,
        user_id=user.id,
        type="suggestion_shown",
        subject_type="suggestion",
        subject_id=suggestion.id,
        payload=SuggestionShownPayload(group_id="idiom.agree"),
    )
    session.commit()

    assert conversation_has_idiom_suggestion(
        session, conversation_id=conversation.id, user_id=user.id
    )

    analysis = analyze("We agree again.")
    analysis.candidates = [
        CandidateSpan(
            text="agree",
            start=3,
            end=8,
            lemma="agree",
            pos="VERB",
            reason="crutch",
        )
    ]
    variables = await build_editor_variables(
        session,
        message="We agree again.",
        analysis=analysis,
        allow_idioms=True,
        conversation_id=conversation.id,
        user_id=user.id,
    )
    assert "idiom.agree" not in {g["id"] for g in variables["groups"]}


@pytest.mark.asyncio
async def test_create_idiom_write_and_grade(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    use_fake(
        FakeLLM(
            {
                "usage_judge": json.dumps(
                    {"correct": True, "explanation": "Fits the shared-understanding sense."}
                )
            }
        )
    )
    exercise = await create_idiom(
        session,
        user_id=user.id,
        group_id="idiom.agree",
        item_type="idiom_write",
        option_id="idiom.agree/on the same page",
        settings=IDIOM_SETTINGS,
    )
    assert exercise.item_type == "idiom_write"
    assert exercise.prompt["word"] == "on the same page"
    assert "answer" not in exercise.prompt
    attempt = await answer_idiom_write(
        session,
        exercise=exercise,
        user_id=user.id,
        response=IdiomWriteResponse(
            sentence="Let's get on the same page before the client call."
        ),
        settings=IDIOM_SETTINGS,
    )
    assert attempt.correct is True
    event = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "exercise_answered")
    ).one()
    assert event.payload["item_type"] == "idiom_write"


@pytest.mark.asyncio
async def test_create_idiom_recognise_with_fake_llm(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    use_fake(
        FakeLLM(
            {
                "compare_gen": json.dumps(
                    {
                        "paragraph": (
                            "Before the launch we need to get on the same page about ownership."
                        ),
                        "option_id": "idiom.agree/on the same page",
                        "choices": [
                            {"id": "idiom.agree/on the same page", "label": "on the same page"},
                            {"id": "idiom.agree/see eye to eye", "label": "see eye to eye"},
                            {"id": "distract:0", "label": "hit the ground running"},
                        ],
                    }
                )
            }
        )
    )
    exercise = await create_idiom(
        session,
        user_id=user.id,
        group_id="idiom.agree",
        item_type="idiom_recognise",
        settings=IDIOM_SETTINGS,
    )
    assert exercise.item_type == "idiom_recognise"
    assert "on the same page" in exercise.prompt["stem"]
    attempt = answer_exercise(
        session,
        exercise=exercise,
        user_id=user.id,
        response=IdiomSelectResponse(selected_id="idiom.agree/on the same page"),
    )
    assert attempt.correct is True


def test_idioms_api_list_and_card(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
    seeded: None,
) -> None:
    user = make_user()
    login_as(user)
    listed = client.get("/api/idioms")
    assert listed.status_code == 200
    body = listed.json()
    assert any(row["id"] == "idiom.agree" for row in body)
    assert any(row["id"] == "idiom.cut" for row in body)
    card = client.get("/api/idioms/idiom.agree")
    assert card.status_code == 200
    payload = card.json()
    assert payload["options"]
    assert all("avoid_when" in opt for opt in payload["options"])
    literary = client.get("/api/idioms/idiom.victory")
    assert literary.status_code == 200
    origin = literary.json()["options"][0].get("origin")
    assert origin and "Pyrrhus" in origin


def test_idiom_write_api(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
    seeded: None,
) -> None:
    user = make_user()
    login_as(user)
    use_fake(
        FakeLLM(
            {
                "usage_judge": json.dumps(
                    {"correct": False, "explanation": "Sounds literal, not idiomatic."}
                )
            }
        )
    )
    created = client.post(
        "/api/exercises/idiom",
        json={
            "group_id": "idiom.agree",
            "item_type": "idiom_write",
            "option_id": "idiom.agree/see eye to eye",
        },
    )
    assert created.status_code == 200
    exercise_id = created.json()["id"]
    assert "answer" not in created.json()
    got = client.get(f"/api/exercises/{exercise_id}")
    assert got.status_code == 200
    assert "answer" not in got.json()
    attempt = client.post(
        f"/api/exercises/{exercise_id}/attempt",
        json={"sentence": "I see eye to eye with the spreadsheet."},
    )
    assert attempt.status_code == 200
    assert attempt.json()["correct"] is False


def test_seeded_idiom_counts(session: Session, seeded: None) -> None:
    groups = session.scalars(
        select(PrecisionGroup).where(PrecisionGroup.kind == "idiom")
    ).all()
    assert len(groups) >= 50
