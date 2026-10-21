"""Editor service: anchoring, caps, review queue, FakeLLM."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.editor.service import analyze_message
from vocab.events import Event
from vocab.lexicon.models import ReviewQueueItem
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        session_secret="test",
        llm_editor_model="fake-editor",
        llm_editor_prompt_version=1,
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
    message = (
        "Yeah the migration was really hard and we had a big problem with the old data, "
        "but we fixed it in the end."
    )
    payload = {
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
        message_id="msg-1",
        message=message,
        partner_previous="How did the migration go?",
        settings=settings,
    )
    assert len(suggestions) == 2
    assert suggestions[0].original_text == "really hard"
    assert message[suggestions[0].span_start : suggestions[0].span_end] == "really hard"
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
    message = "We need to fix the bug."
    payload = {
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
        message_id="msg-2",
        message=message,
        settings=settings,
    )
    queue = list(session.scalars(select(ReviewQueueItem)))
    assert len(queue) == 1
    assert queue[0].proposed_word == "remediate"
    assert queue[0].editor_run_id is not None
