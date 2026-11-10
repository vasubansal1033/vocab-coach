"""Export and erase every row owned by a user."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from vocab.auth.models import Identity, User
from vocab.conversation.models import Conversation, Message, MessageLemmaCount
from vocab.drills.models import Drill, DrillAttempt
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.events import Event
from vocab.llm.models import LlmCall
from vocab.practice.models import SrsCard


def export_user(session: Session, user_id: str) -> dict[str, Any]:
    """Build a JSON-serialisable dump of the user's data (not shared lexicon)."""
    user = session.get(User, user_id)
    if user is None:
        raise ValueError("user not found")
    conversations = list(
        session.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
        )
    )
    return {
        "user": {
            "id": user.id,
            "display_name": user.display_name,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "identities": [
            {"id": i.id, "issuer": i.issuer, "subject": i.subject}
            for i in session.scalars(select(Identity).where(Identity.user_id == user_id))
        ],
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "messages": [
                    {
                        "id": m.id,
                        "role": m.role,
                        "content": m.content,
                        "word_count": m.word_count,
                        "created_at": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in c.messages
                ],
            }
            for c in conversations
        ],
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "subject_type": e.subject_type,
                "subject_id": e.subject_id,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in session.scalars(select(Event).where(Event.user_id == user_id))
        ],
        "srs_cards": [
            {
                "id": c.id,
                "option_id": c.option_id,
                "due_at": c.due_at.isoformat() if c.due_at else None,
                "fsrs_card": c.fsrs_card,
            }
            for c in session.scalars(select(SrsCard).where(SrsCard.user_id == user_id))
        ],
        "drills": [
            {
                "id": d.id,
                "group_id": d.group_id,
                "vague_sentence": d.vague_sentence,
                "intended_word": d.intended_word,
            }
            for d in session.scalars(select(Drill).where(Drill.user_id == user_id))
        ],
        "llm_calls": [
            {
                "id": c.id,
                "role": c.role,
                "model": c.model,
                "prompt_version": c.prompt_version,
                "cost_usd": c.cost_usd,
                "status": c.status,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in session.scalars(select(LlmCall).where(LlmCall.user_id == user_id))
        ],
    }


def delete_user(session: Session, user_id: str) -> None:
    """Remove every row keyed by user_id, then the user row itself."""
    message_ids = list(
        session.scalars(select(Message.id).where(Message.user_id == user_id))
    )
    suggestion_ids = list(
        session.scalars(select(Suggestion.id).where(Suggestion.user_id == user_id))
    )
    if suggestion_ids:
        session.execute(
            delete(SuggestionOption).where(SuggestionOption.suggestion_id.in_(suggestion_ids))
        )
    session.execute(delete(Suggestion).where(Suggestion.user_id == user_id))
    session.execute(delete(EditorRun).where(EditorRun.user_id == user_id))
    if message_ids:
        session.execute(
            delete(MessageLemmaCount).where(MessageLemmaCount.message_id.in_(message_ids))
        )
    session.execute(delete(Message).where(Message.user_id == user_id))
    session.execute(delete(Conversation).where(Conversation.user_id == user_id))
    session.execute(delete(DrillAttempt).where(DrillAttempt.user_id == user_id))
    session.execute(delete(Drill).where(Drill.user_id == user_id))
    session.execute(delete(SrsCard).where(SrsCard.user_id == user_id))
    session.execute(delete(Event).where(Event.user_id == user_id))
    session.execute(delete(LlmCall).where(LlmCall.user_id == user_id))
    session.execute(delete(Identity).where(Identity.user_id == user_id))
    session.execute(delete(User).where(User.id == user_id))
    session.commit()
