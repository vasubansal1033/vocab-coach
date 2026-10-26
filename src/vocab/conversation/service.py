"""Conversation CRUD, message save, accept/dismiss."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.conversation.models import Conversation, Message, MessageLemmaCount
from vocab.editor.models import Suggestion, SuggestionOption
from vocab.events import SuggestionAcceptedPayload, record_event
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


def create_conversation(session: Session, user_id: str, topic: str) -> Conversation:
    """Start a thread; title holds the topic/scenario for the partner prompt."""
    conversation = Conversation(user_id=user_id, title=topic.strip() or "Conversation")
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


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


def suggestions_for_message(session: Session, message_id: str) -> list[Suggestion]:
    return list(
        session.scalars(
            select(Suggestion)
            .where(Suggestion.message_id == message_id)
            .options(selectinload(Suggestion.options))
            .order_by(Suggestion.rank.asc())
        )
    )


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
