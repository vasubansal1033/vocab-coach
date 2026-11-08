"""JSON endpoints consumed by the React SPA under /api."""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from vocab.auth.authorize import authorize
from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.conversation import service
from vocab.conversation.models import Conversation, Message
from vocab.db import get_session
from vocab.drills.models import Drill
from vocab.drills.service import create_drill, grade_attempt
from vocab.editor.models import Suggestion, SuggestionOption
from vocab.editor.service import analyze_message
from vocab.metrics.queries import (
    acceptance_rate,
    crutch_rate,
    crutch_rate_weekly,
    default_window,
    drill_score_weekly,
    lemma_detail,
    lexical_diversity,
    misuse_rate,
    overuse_lift,
    spontaneous_correct_use,
)
from vocab.practice.srs import due_options, review_card

logger = logging.getLogger(__name__)


class TopicIn(BaseModel):
    topic: str = Field(min_length=1)


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


class AcceptIn(BaseModel):
    option_id: str


class DrillAnswerIn(BaseModel):
    answer: str = Field(min_length=1)


class ReviewIn(BaseModel):
    rating: str
    answer: str = ""


def _cloze(example: str, word: str) -> str:
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub("____", example, count=1)


def _user_out(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "display_name": user.display_name,
        "email": user.email,
    }


def _message_out(message: Message) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _conversation_out(conversation: Conversation, *, with_messages: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
    }
    if with_messages:
        data["messages"] = [_message_out(m) for m in conversation.messages]
    return data


def _suggestion_out(suggestion: Suggestion) -> dict[str, Any]:
    return {
        "id": suggestion.id,
        "original_text": suggestion.original_text,
        "question": suggestion.question,
        "options": [
            {
                "id": opt.id,
                "word": opt.word,
                "meaning": opt.meaning,
            }
            for opt in suggestion.options
        ],
    }


def build_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or get_settings()
    router = APIRouter(prefix="/api")

    def _owned_conversation(session: Session, conversation_id: str, user: User) -> Conversation:
        conversation = service.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", conversation)
        return conversation

    @router.get("/me")
    def me(user: User = Depends(current_user)) -> dict[str, Any]:
        return _user_out(user)

    @router.get("/conversations")
    def list_conversations(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        items = service.list_conversations(session, user.id)
        return {"conversations": [_conversation_out(c) for c in items]}

    @router.post("/conversations")
    def create_conversation(
        body: TopicIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        conversation = service.create_conversation(session, user.id, body.topic)
        return _conversation_out(conversation)

    @router.get("/conversations/{conversation_id}")
    def get_conversation(
        conversation_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        conversation = _owned_conversation(session, conversation_id, user)
        return _conversation_out(conversation, with_messages=True)

    @router.post("/conversations/{conversation_id}/messages")
    async def post_message(
        conversation_id: str,
        body: MessageIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        conversation = _owned_conversation(session, conversation_id, user)
        message = service.post_user_message(
            session, conversation=conversation, user_id=user.id, content=body.content
        )
        from vocab.practice.usage import process_message_usage

        await process_message_usage(
            session,
            user_id=user.id,
            conversation_id=conversation.id,
            message=message,
            settings=settings,
        )
        return _message_out(message)

    @router.get("/conversations/{conversation_id}/messages/{message_id}/partner")
    async def partner_sse(
        conversation_id: str,
        message_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> EventSourceResponse:
        conversation = _owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        history = service.chat_history(session, conversation.id)
        topic = conversation.title
        from vocab.practice.srs import due_words as due_word_list

        due = due_word_list(session, user.id, limit=3)
        conv_id = conversation.id
        uid = user.id

        async def event_gen():  # noqa: ANN202
            from vocab.llm.client import stream

            chunks: list[str] = []
            try:
                async for chunk in stream(
                    "partner",
                    {"topic": topic, "due_words": due},
                    user_id=uid,
                    history=history,
                    session=session,
                    settings=settings,
                ):
                    chunks.append(chunk)
                    yield ServerSentEvent(data=chunk, event="token")
                full = "".join(chunks).strip() or "(no reply)"
                service.save_partner_message(
                    session,
                    conversation_id=conv_id,
                    user_id=uid,
                    content=full,
                )
                yield ServerSentEvent(data=full, event="done")
            except Exception as exc:
                logger.exception("partner stream failed")
                yield ServerSentEvent(data=f"Partner reply failed: {exc}", event="error")

        return EventSourceResponse(event_gen())

    @router.get("/conversations/{conversation_id}/messages/{message_id}/feedback")
    async def feedback(
        conversation_id: str,
        message_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        conversation = _owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        partner_previous = service.previous_partner_content(session, conversation.id)
        try:
            await analyze_message(
                session,
                user_id=user.id,
                message_id=message.id,
                message=message.content,
                partner_previous=partner_previous,
                settings=settings,
            )
            suggestions = service.suggestions_for_message(session, message.id)
        except Exception:
            logger.exception("editor failed for message %s", message.id)
            return {"failed": True, "suggestions": []}

        return {
            "failed": False,
            "suggestions": [_suggestion_out(s) for s in suggestions],
        }

    @router.post("/conversations/{conversation_id}/suggestions/{suggestion_id}/accept")
    def accept_suggestion(
        conversation_id: str,
        suggestion_id: str,
        body: AcceptIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        _owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if suggestion is None or suggestion.user_id != user.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        option = session.get(SuggestionOption, body.option_id)
        if option is None or option.suggestion_id != suggestion.id:
            raise HTTPException(status_code=404, detail="Not found")
        service.accept_suggestion(session, suggestion=suggestion, option=option, user_id=user.id)
        return {
            "dismissed": False,
            "accepted_word": option.word,
            "original_text": suggestion.original_text,
        }

    @router.post("/conversations/{conversation_id}/suggestions/{suggestion_id}/dismiss")
    def dismiss_suggestion(
        conversation_id: str,
        suggestion_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        _owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if suggestion is None or suggestion.user_id != user.id:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        service.dismiss_suggestion(session, suggestion=suggestion, user_id=user.id)
        return {
            "dismissed": True,
            "accepted_word": None,
            "original_text": suggestion.original_text,
        }

    @router.get("/dashboard")
    def dashboard(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
        prompt_version: int | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        start, end = default_window()
        weekly = crutch_rate_weekly(session, user.id, start, end)
        drills = drill_score_weekly(session, user.id, start, end)
        overuse = overuse_lift(session, user.id, start, end)
        return {
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "crutch_rate": crutch_rate(session, user.id, start, end),
            "weekly": [{"label": w.label, "rate": w.rate} for w in weekly],
            "overuse": [
                {
                    "word": row.word,
                    "uses": row.uses,
                    "lift": row.lift,
                    "groups": [{"id": g.id, "sense_gloss": g.sense_gloss} for g in row.groups],
                }
                for row in overuse
            ],
            "acceptance": acceptance_rate(
                session,
                user.id,
                start,
                end,
                prompt_version=prompt_version,
                model=model,
            ),
            "spontaneous": spontaneous_correct_use(session, user.id, start, end),
            "misuse": misuse_rate(session, user.id, start, end),
            "drill_weeks": [{"label": w.label, "score": w.score} for w in drills],
            "mtld": lexical_diversity(session, user.id, start, end),
        }

    @router.get("/dashboard/lemma/{lemma}")
    def dashboard_lemma(
        lemma: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        start, end = default_window()
        detail = lemma_detail(session, user.id, start, end, lemma)
        return {
            "lemma": detail.lemma,
            "weekly": [{"label": w.label, "rate": w.rate} for w in detail.weekly],
            "options": [
                {
                    "option_id": o.option_id,
                    "word": o.word,
                    "uses": o.uses,
                    "correct_uses": o.correct_uses,
                }
                for o in detail.options
            ],
        }

    @router.get("/review")
    def review_due(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        options = due_options(session, user.id, limit=1)
        if not options:
            return {"option": None}
        option = options[0]
        return {
            "option": {
                "id": option.id,
                "word": option.word,
                "distinction": option.distinction,
                "example": option.example,
                "cloze": _cloze(option.example, option.word),
            }
        }

    @router.post("/review/{option_id}")
    def review_submit(
        option_id: str,
        body: ReviewIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, str]:
        review_card(
            session,
            user_id=user.id,
            option_id=option_id,
            rating=body.rating,
            source="review_page",
        )
        return {"status": "ok"}

    @router.post("/drills")
    async def drills_create(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        drill = await create_drill(session, user_id=user.id, settings=settings)
        return {
            "id": drill.id,
            "vague_sentence": drill.vague_sentence,
            "intended_word": drill.intended_word,
        }

    @router.get("/drills/{drill_id}")
    def drills_get(
        drill_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        drill = session.get(Drill, drill_id)
        if drill is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", drill)
        return {
            "id": drill.id,
            "vague_sentence": drill.vague_sentence,
            "intended_word": drill.intended_word,
        }

    @router.post("/drills/{drill_id}/attempt")
    async def drills_attempt(
        drill_id: str,
        body: DrillAnswerIn,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        drill = session.get(Drill, drill_id)
        if drill is None:
            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", drill)
        attempt = await grade_attempt(
            session,
            drill=drill,
            user_id=user.id,
            answer=body.answer,
            settings=settings,
        )
        return {
            "answer": attempt.answer,
            "score": attempt.score,
            "grade": attempt.grade,
        }

    return router
