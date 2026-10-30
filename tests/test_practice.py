"""Practice loop: cards, usage, prompted check, rebuild."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation.service import (
    accept_suggestion,
    create_conversation,
    post_user_message,
    save_partner_message,
)
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.events import Event
from vocab.lexicon.service import load_seeds
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.practice.models import SrsCard
from vocab.practice.srs import due_words, ensure_card, rebuild_cards, review_card
from vocab.practice.usage import process_message_usage

JUDGE_SETTINGS = Settings(
    _env_file=None,
    session_secret="test",
    llm_usage_judge_model="fake-judge",
    llm_usage_judge_prompt_version=1,
)


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def seeded(session: Session) -> None:
    load_seeds(session)


def _accept_resolve(session: Session, user: User) -> str:
    option_id = "fix.repair/resolve"
    ensure_card(session, user_id=user.id, option_id=option_id)
    return option_id


@pytest.mark.asyncio
async def test_unprompted_correct_use_reviews_good(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    option_id = _accept_resolve(session, user)
    # Make the card due in the past so due_words would include it later.
    card = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user.id, SrsCard.option_id == option_id)
    ).one()
    card.due_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()

    conversation = create_conversation(session, user.id, "Incident")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We resolved the timeout the next day.",
    )
    use_fake(FakeLLM(fixtures={"usage_judge": '{"correct": true, "explanation": "ok"}'}))
    results = await process_message_usage(
        session,
        user_id=user.id,
        conversation_id=conversation.id,
        message=message,
        settings=JUDGE_SETTINGS,
    )
    assert len(results) == 1
    assert results[0]["prompted"] is False
    assert results[0]["correct"] is True

    used = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "word_used")
    ).one()
    assert used.payload["prompted"] is False
    assert used.payload["correct"] is True

    reviewed = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
    ).all()
    assert any(e.payload["rating"] == "Good" for e in reviewed)


@pytest.mark.asyncio
async def test_partner_prompted_use_skips_review(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    _accept_resolve(session, user)
    conversation = create_conversation(session, user.id, "Incident")
    save_partner_message(
        session,
        conversation_id=conversation.id,
        user_id=user.id,
        content="Did you resolve the outage yet?",
    )
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="Yes, we resolved it with a rate limit.",
    )
    results = await process_message_usage(
        session,
        user_id=user.id,
        conversation_id=conversation.id,
        message=message,
    )
    assert len(results) == 1
    assert results[0]["prompted"] is True
    used = session.scalars(
        select(Event).where(Event.user_id == user.id, Event.type == "word_used")
    ).one()
    assert used.payload["prompted"] is True
    assert (
        session.scalars(
            select(Event).where(Event.user_id == user.id, Event.type == "card_reviewed")
        ).first()
        is None
    )


def test_due_words_for_partner(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    option_id = _accept_resolve(session, user)
    card = session.scalars(
        select(SrsCard).where(SrsCard.option_id == option_id, SrsCard.user_id == user.id)
    ).one()
    card.due_at = datetime.now(UTC) - timedelta(hours=1)
    session.commit()
    words = due_words(session, user.id, limit=3)
    assert "resolve" in words


def test_rebuild_matches_reviewed_state(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    option_id = _accept_resolve(session, user)
    before = review_card(
        session,
        user_id=user.id,
        option_id=option_id,
        rating="Good",
        source="review_page",
    )
    stability_before = before.fsrs_card.get("stability")
    state_before = before.fsrs_card.get("state")

    rebuild_cards(session, user.id)
    after = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user.id, SrsCard.option_id == option_id)
    ).one()
    assert after.fsrs_card.get("stability") == stability_before
    assert after.fsrs_card.get("state") == state_before


def test_accept_creates_card(
    session: Session, make_user: Callable[..., User], seeded: None
) -> None:
    user = make_user()
    conversation = create_conversation(session, user.id, "T")
    message = post_user_message(
        session, conversation=conversation, user_id=user.id, content="we fixed it"
    )
    run = EditorRun(
        message_id=message.id,
        user_id=user.id,
        llm_call_id=None,
        output={},
    )
    session.add(run)
    session.flush()
    suggestion = Suggestion(
        editor_run_id=run.id,
        message_id=message.id,
        user_id=user.id,
        original_text="fixed",
        span_start=3,
        span_end=8,
        group_id="fix.repair",
        question=None,
        rank=0,
    )
    session.add(suggestion)
    session.flush()
    option = SuggestionOption(
        suggestion_id=suggestion.id,
        option_id="fix.repair/resolve",
        word="resolve",
        meaning="cause removed",
        rank=0,
    )
    session.add(option)
    session.commit()
    accept_suggestion(session, suggestion=suggestion, option=option, user_id=user.id)
    card = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user.id, SrsCard.option_id == "fix.repair/resolve")
    ).one()
    assert card.due_at is not None
