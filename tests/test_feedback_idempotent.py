"""GET feedback must not re-call the editor or duplicate suggestion_shown."""

from __future__ import annotations

import json
from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.service import create_conversation, post_user_message
from vocab.db import get_session
from vocab.editor.models import EditorRun, Suggestion
from vocab.events import Event
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.main import create_app


def _app(session: Session, user: User) -> TestClient:
    settings = Settings(
        _env_file=None,
        session_secret="test-session-secret",
        llm_partner_model="fake-partner",
        llm_editor_model="fake-editor",
        llm_partner_prompt_version=1,
        llm_editor_prompt_version=3,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app, follow_redirects=False)


def test_api_feedback_is_idempotent(
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

    path = f"/api/conversations/{conversation.id}/messages/{message.id}/feedback"
    first = client.get(path, headers={"accept": "application/json"})
    second = client.get(path, headers={"accept": "application/json"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["failed"] is False
    assert len(first.json()["suggestions"]) == len(second.json()["suggestions"]) == 1

    runs = session.scalar(
        select(func.count()).select_from(EditorRun).where(EditorRun.message_id == message.id)
    )
    suggestions = session.scalar(
        select(func.count()).select_from(Suggestion).where(Suggestion.message_id == message.id)
    )
    shown = session.scalar(
        select(func.count())
        .select_from(Event)
        .where(Event.user_id == user.id, Event.type == "suggestion_shown")
    )
    assert runs == 1
    assert suggestions == 1
    assert shown == 1
