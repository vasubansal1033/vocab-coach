"""Build editor feedback for one user message (API + HTML share this)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings
from vocab.conversation.highlight import highlight_message
from vocab.conversation.models import Conversation, Message
from vocab.conversation.service import previous_partner_content
from vocab.editor.models import EditorRun, Suggestion
from vocab.editor.service import analyze_message

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedbackResult:
    """Normalized feedback payload for JSON or HTML templates."""

    failed: bool
    content: str
    overview: str | None
    highlighted_html: str
    keep: list[str]
    suggestions: list[Suggestion]
    why_by_original: dict[str, str]


def _why_by_original(output: dict[str, Any] | None) -> dict[str, str]:
    if not output:
        return {}
    mapping: dict[str, str] = {}
    for item in output.get("suggestions") or []:
        original = item.get("original")
        why = item.get("why")
        if isinstance(original, str) and isinstance(why, str):
            mapping[original] = why
    return mapping


def latest_editor_run(
    session: Session, *, message_id: str, user_id: str
) -> EditorRun | None:
    """Most recent editor run for this message (idempotent feedback key)."""
    return session.scalars(
        select(EditorRun)
        .where(EditorRun.message_id == message_id, EditorRun.user_id == user_id)
        .order_by(EditorRun.created_at.desc())
    ).first()


def suggestions_for_run(session: Session, editor_run_id: str) -> list[Suggestion]:
    """Suggestions belonging to one editor run only."""
    return list(
        session.scalars(
            select(Suggestion)
            .where(Suggestion.editor_run_id == editor_run_id)
            .options(selectinload(Suggestion.options))
            .order_by(Suggestion.rank.asc())
        )
    )


def _result_from_run(
    *,
    message: Message,
    run: EditorRun,
    suggestions: list[Suggestion],
) -> FeedbackResult:
    output = run.output if isinstance(run.output, dict) else {}
    keep = list(output.get("keep") or [])
    return FeedbackResult(
        failed=False,
        content=message.content,
        overview=output.get("overview") if isinstance(output.get("overview"), str) else None,
        highlighted_html=highlight_message(message.content, suggestions, keep=keep),
        keep=keep,
        suggestions=suggestions,
        why_by_original=_why_by_original(output),
    )


async def ensure_message_feedback(
    session: Session,
    *,
    conversation: Conversation,
    message: Message,
    user_id: str,
    settings: Settings,
) -> FeedbackResult:
    """Return feedback for a message, reusing an existing editor run when present.

    GET feedback must be idempotent: no second LLM call, no duplicate suggestions,
    no extra suggestion_shown events.
    """
    existing = latest_editor_run(session, message_id=message.id, user_id=user_id)
    if existing is not None:
        return _result_from_run(
            message=message,
            run=existing,
            suggestions=suggestions_for_run(session, existing.id),
        )

    partner_previous = previous_partner_content(session, conversation.id)
    try:
        await analyze_message(
            session,
            user_id=user_id,
            message_id=message.id,
            message=message.content,
            partner_previous=partner_previous,
            conversation_title=conversation.title,
            feedback_expectations=conversation.feedback_expectations,
            settings=settings,
        )
    except Exception:
        logger.exception("editor failed for message %s", message.id)
        return FeedbackResult(
            failed=True,
            content=message.content,
            overview=None,
            highlighted_html="",
            keep=[],
            suggestions=[],
            why_by_original={},
        )

    run = latest_editor_run(session, message_id=message.id, user_id=user_id)
    if run is None:
        return FeedbackResult(
            failed=True,
            content=message.content,
            overview=None,
            highlighted_html="",
            keep=[],
            suggestions=[],
            why_by_original={},
        )
    return _result_from_run(
        message=message,
        run=run,
        suggestions=suggestions_for_run(session, run.id),
    )
