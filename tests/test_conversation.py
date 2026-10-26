"""Conversation UI: post message, feedback, accept/dismiss, editor failure."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.models import Message, MessageLemmaCount
from vocab.conversation.service import create_conversation, post_user_message
from vocab.db import get_session
from vocab.events import Event
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.main import create_app


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
        llm_partner_prompt_version=1,
        llm_editor_prompt_version=1,
        **settings_kw,  # type: ignore[arg-type]
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app, follow_redirects=False)


@pytest.mark.asyncio
async def test_post_message_stores_lemma_counts(
    session: Session, make_user: Callable[..., User]
) -> None:
    user = make_user()
    conversation = create_conversation(session, user.id, "Migration chat")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We fixed the big problem.",
    )
    assert message.role == "user"
    assert message.word_count > 0
    n = session.scalar(
        select(func.count())
        .select_from(MessageLemmaCount)
        .where(MessageLemmaCount.message_id == message.id)
    )
    assert n and n > 0


def test_feedback_accept_and_dismiss_events(
    session: Session, make_user: Callable[..., User]
) -> None:
    load_seeds(session)
    user = make_user()
    client = _app(session, user)
    conversation = create_conversation(session, user.id, "Topic")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We need to fix that thing.",
    )
    payload = {
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
    use_fake(
        FakeLLM(
            fixtures={"editor": json.dumps(payload)},
            stream_chunks={"partner": ["Hello ", "there."]},
        )
    )

    feedback = client.get(f"/conversations/{conversation.id}/messages/{message.id}/feedback")
    assert feedback.status_code == 200
    assert b"resolve" in feedback.content

    shown = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "suggestion_shown")
    ).all()
    assert len(shown) >= 1

    # Pull suggestion option id from DB
    from vocab.editor.models import Suggestion, SuggestionOption

    suggestion = session.scalars(
        select(Suggestion).where(Suggestion.message_id == message.id)
    ).one()
    option = session.scalars(
        select(SuggestionOption).where(SuggestionOption.suggestion_id == suggestion.id)
    ).one()

    accepted = client.post(
        f"/conversations/{conversation.id}/suggestions/{suggestion.id}/accept",
        data={"option_id": option.id},
    )
    assert accepted.status_code == 200
    assert b"Accepted" in accepted.content
    assert session.scalars(
        select(Event).where(Event.type == "suggestion_accepted", Event.user_id == user.id)
    ).first()

    # Second suggestion path: dismiss
    message2 = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="It was really hard.",
    )
    payload2 = {
        "suggestions": [
            {
                "original": "really hard",
                "group_id": "hard.difficulty",
                "options": [
                    {
                        "word": "difficult",
                        "meaning": "needs effort",
                        "option_id": "hard.difficulty/difficult",
                    }
                ],
                "question": None,
                "why": "vague",
            }
        ],
        "keep": [],
    }
    use_fake(FakeLLM(fixtures={"editor": json.dumps(payload2)}))
    client.get(f"/conversations/{conversation.id}/messages/{message2.id}/feedback")
    suggestion2 = session.scalars(
        select(Suggestion).where(Suggestion.message_id == message2.id)
    ).one()
    dismissed = client.post(
        f"/conversations/{conversation.id}/suggestions/{suggestion2.id}/dismiss"
    )
    assert dismissed.status_code == 200
    assert session.scalars(
        select(Event).where(Event.type == "suggestion_dismissed", Event.user_id == user.id)
    ).first()


def test_editor_failure_shows_no_feedback(session: Session, make_user: Callable[..., User]) -> None:
    user = make_user()
    client = _app(session, user)
    conversation = create_conversation(session, user.id, "Topic")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="Hello there friend.",
    )
    use_fake(FakeLLM(fixtures={"editor": ["not-valid-json", "still-not-json"]}))
    response = client.get(f"/conversations/{conversation.id}/messages/{message.id}/feedback")
    assert response.status_code == 200
    assert b"No feedback for this message" in response.content


def test_partner_sse_saves_message(session: Session, make_user: Callable[..., User]) -> None:
    user = make_user()
    client = _app(session, user)
    conversation = create_conversation(session, user.id, "Topic")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="How is it going?",
    )
    use_fake(FakeLLM(fixtures={"partner": "Hi!"}, stream_chunks={"partner": ["Hi", "!"]}))
    with client.stream(
        "GET",
        f"/conversations/{conversation.id}/messages/{message.id}/partner",
    ) as response:
        assert response.status_code == 200
        body = b"".join(response.iter_bytes())
    assert b"Hi" in body
    partners = session.scalars(
        select(Message).where(Message.conversation_id == conversation.id, Message.role == "partner")
    ).all()
    assert len(partners) == 1
    assert "Hi" in partners[0].content
