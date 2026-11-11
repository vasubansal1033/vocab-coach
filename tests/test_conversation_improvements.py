"""Conversation improvements: retry, recap, flow mode."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from lexicon_fixture import seed_lexicon
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.models import Message
from vocab.conversation.service import (
    accept_suggestion,
    conversation_recap,
    create_conversation,
    dismiss_suggestion,
    post_user_message,
    retry_suggestion,
)
from vocab.db import get_session
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.events import (
    Event,
    SuggestionShownPayload,
    record_event,
)
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.main import create_app
from vocab.practice.usage import process_message_usage


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


def _app(session: Session, user: User, **settings_kw: object) -> TestClient:
    settings = Settings(
        _env_file=None,
        session_secret="test-session-secret",
        llm_partner_model="fake-partner",
        llm_editor_model="fake-editor",
        llm_usage_judge_model="fake-judge",
        llm_partner_prompt_version=1,
        llm_editor_prompt_version=3,
        llm_usage_judge_prompt_version=1,
        **settings_kw,  # type: ignore[arg-type]
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app, follow_redirects=False)


def _seed_suggestion(
    session: Session,
    *,
    user: User,
    message: Message,
    original: str,
    span_start: int,
    span_end: int,
    word: str = "resolve",
    option_id: str = "fix.repair/resolve",
    group_id: str = "fix.repair",
    rank: int = 0,
    record_shown: bool = True,
) -> tuple[Suggestion, SuggestionOption]:
    run = EditorRun(
        message_id=message.id,
        user_id=user.id,
        llm_call_id=None,
        output={"suggestions": [], "keep": []},
    )
    session.add(run)
    session.flush()
    suggestion = Suggestion(
        editor_run_id=run.id,
        message_id=message.id,
        user_id=user.id,
        original_text=original,
        span_start=span_start,
        span_end=span_end,
        group_id=group_id,
        question=None,
        rank=rank,
    )
    session.add(suggestion)
    session.flush()
    option = SuggestionOption(
        suggestion_id=suggestion.id,
        option_id=option_id,
        word=word,
        meaning="cause removed",
        rank=0,
    )
    session.add(option)
    session.commit()
    if record_shown:
        record_event(
            session,
            user_id=user.id,
            type="suggestion_shown",
            subject_type="suggestion",
            subject_id=suggestion.id,
            payload=SuggestionShownPayload(group_id=group_id),
        )
        session.commit()
    return suggestion, option


def test_create_conversation_stores_flow_and_idioms(
    session: Session, make_user: Callable[..., User]
) -> None:
    user = make_user()
    client = _app(session, user)
    response = client.post(
        "/api/conversations",
        headers={"accept": "application/json"},
        json={
            "name": "Team chat update",
            "feedback_expectations": "Neutral and brief",
            "flow_mode": True,
            "allow_idioms": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["flow_mode"] is True
    assert body["allow_idioms"] is True
    got = client.get(
        f"/api/conversations/{body['id']}", headers={"accept": "application/json"}
    )
    assert got.json()["flow_mode"] is True
    assert got.json()["allow_idioms"] is True


@pytest.mark.asyncio
async def test_retry_accepts_once_and_prompted_use(
    session: Session, make_user: Callable[..., User]
) -> None:
    seed_lexicon(session)
    user = make_user()
    conversation = create_conversation(session, user.id, "Retry")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We fixed the bug.",
    )
    # "fixed" starts at index 3
    suggestion, option = _seed_suggestion(
        session,
        user=user,
        message=message,
        original="fixed",
        span_start=3,
        span_end=8,
    )
    rewritten = retry_suggestion(
        session, suggestion=suggestion, option=option, user_id=user.id
    )
    assert rewritten == "We resolve the bug."
    accept_suggestion(session, suggestion=suggestion, option=option, user_id=user.id)
    accepted = session.scalars(
        select(Event).where(
            Event.user_id == user.id,
            Event.type == "suggestion_accepted",
            Event.subject_id == suggestion.id,
        )
    ).all()
    assert len(accepted) == 1
    retried = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "suggestion_retried")
    ).one()
    assert retried.payload["word"] == "resolve"

    follow = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We resolve the timeout next.",
    )
    use_fake(FakeLLM(fixtures={"usage_judge": '{"correct": true, "explanation": "ok"}'}))
    results = await process_message_usage(
        session,
        user_id=user.id,
        conversation_id=conversation.id,
        message=follow,
        settings=Settings(
            _env_file=None,
            session_secret="test",
            llm_usage_judge_model="fake-judge",
            llm_usage_judge_prompt_version=1,
        ),
    )
    assert len(results) == 1
    assert results[0]["prompted"] is True
    assert (
        session.scalars(
            select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
        ).first()
        is None
    )


@pytest.mark.asyncio
async def test_conversation_recap_parts(
    session: Session, make_user: Callable[..., User]
) -> None:
    seed_lexicon(session)
    user = make_user()
    conversation = create_conversation(session, user.id, "Recap seed")
    msg1 = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We fixed the first issue. Then we made a big problem worse.",
    )
    msg2 = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="It was really hard overall.",
    )
    # Accepted suggestion on first message (rank 0).
    s_accepted, opt_accepted = _seed_suggestion(
        session,
        user=user,
        message=msg1,
        original="fixed",
        span_start=3,
        span_end=8,
        word="resolve",
        option_id="fix.repair/resolve",
        rank=0,
    )
    accept_suggestion(session, suggestion=s_accepted, option=opt_accepted, user_id=user.id)

    # Shown, not dismissed, for fill words (rank 1).
    _seed_suggestion(
        session,
        user=user,
        message=msg1,
        original="big problem",
        span_start=msg1.content.index("big problem"),
        span_end=msg1.content.index("big problem") + len("big problem"),
        word="incident",
        option_id=None,
        group_id=None,
        rank=1,
    )

    # Open suggestion for rewrite sentence (rank 0 on second message).
    s_open, _opt_open = _seed_suggestion(
        session,
        user=user,
        message=msg2,
        original="really hard",
        span_start=msg2.content.index("really hard"),
        span_end=msg2.content.index("really hard") + len("really hard"),
        word="difficult",
        option_id="hard.difficulty/difficult",
        group_id="hard.difficulty",
        rank=0,
    )
    # Dismiss a decoy so it is excluded from rewrite.
    s_dismissed, _ = _seed_suggestion(
        session,
        user=user,
        message=msg2,
        original="overall",
        span_start=msg2.content.index("overall"),
        span_end=msg2.content.index("overall") + len("overall"),
        word="altogether",
        option_id=None,
        group_id=None,
        rank=1,
    )
    dismiss_suggestion(session, suggestion=s_dismissed, user_id=user.id)

    recap = await conversation_recap(session, conversation=conversation, user_id=user.id)
    assert any(w.word == "resolve" and w.source == "accepted" for w in recap.words_to_keep)
    assert any(w.word == "incident" for w in recap.words_to_keep)
    assert len(recap.words_to_keep) <= 3
    assert any(c.lemma == "fix" for c in recap.crutch_words) or any(
        c.lemma == "make" for c in recap.crutch_words
    ) or any(c.lemma == "hard" for c in recap.crutch_words) or any(
        c.lemma == "big" for c in recap.crutch_words
    ) or any(c.lemma == "problem" for c in recap.crutch_words)
    assert recap.crutch_words == sorted(
        recap.crutch_words, key=lambda c: (-c.count, c.lemma)
    )
    assert recap.rewrite_sentence is not None
    assert "really hard" in recap.rewrite_sentence
    assert s_open.id  # open suggestion drives rewrite sentence


@pytest.mark.asyncio
async def test_flow_mode_defers_editor_until_recap(
    session: Session, make_user: Callable[..., User]
) -> None:
    seed_lexicon(session)
    user = make_user()
    client = _app(session, user)
    conversation = create_conversation(
        session, user.id, "Flow", flow_mode=True, allow_idioms=False
    )
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We need to fix that thing.",
    )
    payload = {
        "overview": "Vague verb.",
        "suggestions": [
            {
                "original": "fix",
                "group_id": "fix.repair",
                "options": [
                    {
                        "word": "resolve",
                        "meaning": "cause removed",
                        "option_id": "fix.repair/resolve",
                    }
                ],
                "question": None,
                "why": "vague",
            }
        ],
        "keep": [],
    }
    use_fake(FakeLLM(fixtures={"editor": json.dumps(payload)}))

    # Per-message feedback must not run the editor in flow mode.
    feedback = client.get(
        f"/api/conversations/{conversation.id}/messages/{message.id}/feedback",
        headers={"accept": "application/json"},
    )
    assert feedback.status_code == 200
    assert feedback.json()["suggestions"] == []
    editor_run_count = session.scalar(
        select(func.count()).select_from(EditorRun).where(EditorRun.user_id == user.id)
    )
    assert editor_run_count == 0
    assert (
        session.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.user_id == user.id, Event.type == "suggestion_shown")
        )
        == 0
    )

    recap = client.get(
        f"/api/conversations/{conversation.id}/recap",
        headers={"accept": "application/json"},
    )
    assert recap.status_code == 200
    editor_run_count_after = session.scalar(
        select(func.count()).select_from(EditorRun).where(EditorRun.user_id == user.id)
    )
    assert editor_run_count_after is not None and editor_run_count_after >= 1
    # Every user message has an editor run after recap.
    user_msgs = session.scalars(
        select(Message).where(
            Message.conversation_id == conversation.id, Message.role == "user"
        )
    ).all()
    for msg in user_msgs:
        assert (
            session.scalars(
                select(EditorRun).where(
                    EditorRun.message_id == msg.id, EditorRun.user_id == user.id
                )
            ).first()
            is not None
        )


def test_api_retry_endpoint(session: Session, make_user: Callable[..., User]) -> None:
    seed_lexicon(session)
    user = make_user()
    client = _app(session, user)
    conversation = create_conversation(session, user.id, "API retry")
    message = post_user_message(
        session, conversation=conversation, user_id=user.id, content="We fixed it."
    )
    suggestion, option = _seed_suggestion(
        session,
        user=user,
        message=message,
        original="fixed",
        span_start=3,
        span_end=8,
    )
    response = client.post(
        f"/api/conversations/{conversation.id}/suggestions/{suggestion.id}/retry",
        headers={"accept": "application/json"},
        json={"option_id": option.id},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "We resolve it."
