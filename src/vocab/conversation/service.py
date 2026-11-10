"""Conversation CRUD, message save, accept/dismiss."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from vocab.conversation.models import Conversation, Message, MessageLemmaCount
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.events import SuggestionAcceptedPayload, record_event
from vocab.lexicon.models import ReviewQueueItem
from vocab.nlp.analyzer import analyze
from vocab.nlp.persist import lemma_count_rows, word_count_value


def list_conversations(session: Session, user_id: str) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(session.scalars(stmt))


def get_conversation(session: Session, conversation_id: str) -> Conversation | None:
    return session.scalars(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    ).first()


def create_conversation(
    session: Session,
    user_id: str,
    name: str,
    *,
    feedback_expectations: str | None = None,
) -> Conversation:
    """Start a thread; title is the name/scenario; optional editor brief for domain vocabulary."""
    brief = (feedback_expectations or "").strip() or None
    conversation = Conversation(
        user_id=user_id,
        title=name.strip() or "Conversation",
        feedback_expectations=brief,
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def delete_conversation(session: Session, conversation: Conversation) -> None:
    """Remove one conversation and its message-linked editor rows. Keep events for metrics.

    Caller must authorize ownership before calling.
    """
    message_ids = list(
        session.scalars(select(Message.id).where(Message.conversation_id == conversation.id))
    )
    if message_ids:
        run_ids = list(
            session.scalars(select(EditorRun.id).where(EditorRun.message_id.in_(message_ids)))
        )
        suggestion_ids = list(
            session.scalars(select(Suggestion.id).where(Suggestion.message_id.in_(message_ids)))
        )
        if suggestion_ids:
            session.execute(
                delete(SuggestionOption).where(
                    SuggestionOption.suggestion_id.in_(suggestion_ids)
                )
            )
        session.execute(delete(Suggestion).where(Suggestion.message_id.in_(message_ids)))
        if run_ids:
            # review_queue.editor_run_id FK blocks editor_runs deletes.
            session.execute(
                delete(ReviewQueueItem).where(ReviewQueueItem.editor_run_id.in_(run_ids))
            )
            session.execute(delete(EditorRun).where(EditorRun.id.in_(run_ids)))
        session.execute(
            delete(MessageLemmaCount).where(MessageLemmaCount.message_id.in_(message_ids))
        )
        session.execute(delete(Message).where(Message.id.in_(message_ids)))
    session.execute(delete(Conversation).where(Conversation.id == conversation.id))
    session.commit()


def post_user_message(
    session: Session,
    *,
    conversation: Conversation,
    user_id: str,
    content: str,
) -> Message:
    """Store a user message and its lemma counts."""
    text = content.strip()
    analysis = analyze(text)
    message = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=text,
        word_count=word_count_value(analysis),
    )
    session.add(message)
    session.flush()
    for row in lemma_count_rows(analysis):
        session.add(
            MessageLemmaCount(
                message_id=message.id,
                user_id=user_id,
                lemma=row["lemma"],
                surface=row["surface"],
                count=row["count"],
            )
        )
    session.commit()
    session.refresh(message)
    return message


def save_partner_message(
    session: Session,
    *,
    conversation_id: str,
    user_id: str,
    content: str,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="partner",
        content=content,
        word_count=0,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def chat_history(session: Session, conversation_id: str) -> list[dict[str, str]]:
    """Prior turns as LiteLLM chat messages (user/assistant)."""
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    history: list[dict[str, str]] = []
    for msg in messages:
        role = "user" if msg.role == "user" else "assistant"
        history.append({"role": role, "content": msg.content})
    return history


def previous_partner_content(session: Session, conversation_id: str) -> str | None:
    msg = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role == "partner")
        .order_by(Message.created_at.desc())
    ).first()
    return msg.content if msg else None


def accept_suggestion(
    session: Session,
    *,
    suggestion: Suggestion,
    option: SuggestionOption,
    user_id: str,
) -> Suggestion:
    record_event(
        session,
        user_id=user_id,
        type="suggestion_accepted",
        subject_type="suggestion",
        subject_id=suggestion.id,
        payload=SuggestionAcceptedPayload(option_id=option.option_id, word=option.word),
    )
    session.commit()
    if option.option_id:
        from vocab.practice.srs import ensure_card

        ensure_card(session, user_id=user_id, option_id=option.option_id)
    return suggestion


def dismiss_suggestion(
    session: Session,
    *,
    suggestion: Suggestion,
    user_id: str,
) -> Suggestion:
    record_event(
        session,
        user_id=user_id,
        type="suggestion_dismissed",
        subject_type="suggestion",
        subject_id=suggestion.id,
        payload=None,
    )
    session.commit()
    return suggestion
