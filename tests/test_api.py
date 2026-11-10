"""JSON API used by the React SPA."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from metrics_fixture import seed_metrics_fixture
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.lexicon.service import load_seeds


def test_api_me_and_dashboard(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user()
    seed_metrics_fixture(session, user)
    login_as(user)

    me = client.get("/api/me", headers={"accept": "application/json"})
    assert me.status_code == 200
    assert me.json()["id"] == user.id

    dash = client.get("/api/dashboard", headers={"accept": "application/json"})
    assert dash.status_code == 200
    body = dash.json()
    assert body["crutch_rate"] == 500.0
    assert body["acceptance"] == 0.5


def test_api_create_conversation(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    load_seeds(session)
    user = make_user()
    login_as(user)
    created = client.post(
        "/api/conversations",
        headers={"accept": "application/json"},
        json={
            "name": "Ship review",
            "feedback_expectations": "Prefer product launch vocabulary",
        },
    )
    assert created.status_code == 200
    body = created.json()
    assert body["title"] == "Ship review"
    assert body["feedback_expectations"] == "Prefer product launch vocabulary"
    conversation_id = body["id"]
    listed = client.get("/api/conversations", headers={"accept": "application/json"})
    assert listed.status_code == 200
    assert any(c["id"] == conversation_id for c in listed.json()["conversations"])

    deleted = client.delete(
        f"/api/conversations/{conversation_id}",
        headers={"accept": "application/json"},
    )
    assert deleted.status_code == 204
    listed_after = client.get("/api/conversations", headers={"accept": "application/json"})
    assert all(c["id"] != conversation_id for c in listed_after.json()["conversations"])


def test_api_delete_conversation_with_editor_rows(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    """review_queue FK must not block conversation delete after feedback ran."""
    from sqlalchemy import select

    from vocab.conversation.models import Conversation
    from vocab.conversation.service import create_conversation, post_user_message
    from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
    from vocab.lexicon.models import ReviewQueueItem

    load_seeds(session)
    user = make_user()
    login_as(user)
    conversation = create_conversation(session, user.id, "Delete me")
    message = post_user_message(
        session,
        conversation=conversation,
        user_id=user.id,
        content="We need to fix that thing.",
    )
    run = EditorRun(
        user_id=user.id,
        message_id=message.id,
        output={"overview": "Vague.", "suggestions": [], "keep": []},
    )
    session.add(run)
    session.flush()
    suggestion = Suggestion(
        editor_run_id=run.id,
        message_id=message.id,
        user_id=user.id,
        original_text="fix",
        span_start=11,
        span_end=14,
        group_id="fix.repair",
        question=None,
        rank=0,
    )
    session.add(suggestion)
    session.flush()
    session.add(
        SuggestionOption(
            suggestion_id=suggestion.id,
            option_id=None,
            word="remediate",
            meaning="correct systematically",
            rank=0,
        )
    )
    session.add(
        ReviewQueueItem(
            editor_run_id=run.id,
            head_lemma="fix",
            proposed_word="remediate",
            distinction="correct systematically",
            example="",
            status="pending",
        )
    )
    session.commit()
    conversation_id = conversation.id
    run_id = run.id

    deleted = client.delete(
        f"/api/conversations/{conversation_id}",
        headers={"accept": "application/json"},
    )
    assert deleted.status_code == 204
    session.expire_all()
    assert session.get(Conversation, conversation_id) is None
    assert session.get(EditorRun, run_id) is None
    assert (
        session.scalars(
            select(ReviewQueueItem).where(ReviewQueueItem.proposed_word == "remediate")
        ).first()
        is None
    )


def test_api_create_conversation_topic_alias(
    client: TestClient,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user()
    login_as(user)
    created = client.post(
        "/api/conversations",
        headers={"accept": "application/json"},
        json={"topic": "Legacy topic field"},
    )
    assert created.status_code == 200
    assert created.json()["title"] == "Legacy topic field"
    assert created.json()["feedback_expectations"] is None
