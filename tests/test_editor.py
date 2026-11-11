"""Editor service: anchoring, caps, review queue, FakeLLM."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.service import create_conversation, post_user_message
from vocab.editor.service import analyze_message
from vocab.events import Event
from vocab.lexicon.models import ReviewQueueItem
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM


@pytest.fixture(autouse=True)
def _clear_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    use_fake(None)

    async def _no_network_hints(
        lemmas: list[tuple[str, str | None]],
        *,
        timeout: float = 2.0,
    ) -> dict[str, list[str]]:
        _ = lemmas, timeout
        return {"fix": ["repair", "resolve", "patch"]}

    monkeypatch.setattr("vocab.editor.service.synonym_hints", _no_network_hints)
    yield
    use_fake(None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        session_secret="test",
        llm_editor_model="fake-editor",
        llm_editor_prompt_version=4,
        editor_max_suggestions=2,
    )


@pytest.mark.asyncio
async def test_analyze_message_anchors_and_records(
    session: Session,
    make_user: Callable[..., User],
    settings: Settings,
) -> None:
    load_seeds(session)
    user = make_user()
    conversation = create_conversation(session, user.id, "Migration")
    text = (
        "Yeah the migration was really hard and we had a big problem with the old data, "
        "but we fixed it in the end."
    )
    message = post_user_message(
        session, conversation=conversation, user_id=user.id, content=text
    )
    payload = {
        "overview": "A few vague spots.",
        "suggestions": [
            {
                "original": "really hard",
                "group_id": "hard.difficulty",
                "options": [
                    {
                        "word": "difficult",
                        "meaning": "requires effort",
                        "option_id": "hard.difficulty/difficult",
                    }
                ],
                "question": None,
                "why": "vague intensity",
            },
            {
                "original": "fixed",
                "group_id": "fix.repair",
                "options": [
                    {
                        "word": "resolve",
                        "meaning": "cause removed",
                        "option_id": "fix.repair/resolve",
                    }
                ],
                "question": None,
                "why": "vague verb",
            },
            {
                "original": "NOT IN MESSAGE",
                "group_id": None,
                "options": [{"word": "x", "meaning": "y", "option_id": None}],
                "question": None,
                "why": "should drop",
            },
        ],
        "keep": ["migration"],
    }
    use_fake(FakeLLM(fixtures={"editor": json.dumps(payload)}))

    suggestions = await analyze_message(
        session,
        user_id=user.id,
        message_id=message.id,
        message=text,
        partner_previous="How did the migration go?",
        settings=settings,
    )
    assert len(suggestions) == 2
    assert suggestions[0].original_text == "really hard"
    assert text[suggestions[0].span_start : suggestions[0].span_end] == "really hard"
    events = list(session.scalars(select(Event).where(Event.user_id == user.id)))
    assert len(events) == 2
    assert all(e.type == "suggestion_shown" for e in events)


@pytest.mark.asyncio
async def test_unknown_option_goes_to_review_queue(
    session: Session,
    make_user: Callable[..., User],
    settings: Settings,
) -> None:
    load_seeds(session)
    user = make_user()
    conversation = create_conversation(session, user.id, "Bug")
    text = "We need to fix the bug."
    message = post_user_message(
        session, conversation=conversation, user_id=user.id, content=text
    )
    payload = {
        "overview": "Vague verb.",
        "suggestions": [
            {
                "original": "fix",
                "group_id": "fix.repair",
                "options": [
                    {
                        "word": "remediate",
                        "meaning": "correct systematically",
                        "option_id": None,
                    }
                ],
                "question": None,
                "why": "vague",
            }
        ],
        "keep": [],
    }
    use_fake(FakeLLM(fixtures={"editor": json.dumps(payload)}))
    await analyze_message(
        session,
        user_id=user.id,
        message_id=message.id,
        message=text,
        settings=settings,
    )
    queued = session.scalars(select(ReviewQueueItem)).all()
    assert any(item.proposed_word == "remediate" for item in queued)
