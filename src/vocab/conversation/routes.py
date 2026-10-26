"""Chat pages: list, new, view, post, partner SSE, feedback, accept/dismiss."""

from __future__ import annotations

import html
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from vocab.auth.authorize import authorize
from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.conversation import service
from vocab.conversation.highlight import highlight_message
from vocab.conversation.models import Conversation, Message
from vocab.db import get_session
from vocab.editor.models import Suggestion, SuggestionOption
from vocab.editor.service import analyze_message

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def build_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or get_settings()
    router = APIRouter()

    def _load_owned_conversation(
        session: Session, conversation_id: str, user: User
    ) -> Conversation:
        conversation = service.get_conversation(session, conversation_id)
        if conversation is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", conversation)
        return conversation

    @router.get("/conversations", response_class=HTMLResponse)
    def conversation_list(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        items = service.list_conversations(session, user.id)
        return templates.TemplateResponse(
            request,
            "conversation/list.html",
            {"user": user, "conversations": items},
        )

    @router.get("/conversations/new", response_class=HTMLResponse)
    def new_conversation_form(
        request: Request,
        user: User = Depends(current_user),
    ) -> HTMLResponse:
        return templates.TemplateResponse(request, "conversation/new.html", {"user": user})

    @router.post("/conversations/new")
    def new_conversation(
        topic: str = Form(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        conversation = service.create_conversation(session, user.id, topic)
        return RedirectResponse(url=f"/conversations/{conversation.id}", status_code=303)

    @router.get("/conversations/{conversation_id}", response_class=HTMLResponse)
    def conversation_view(
        conversation_id: str,
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        return templates.TemplateResponse(
            request,
            "conversation/view.html",
            {"user": user, "conversation": conversation},
        )

    @router.post("/conversations/{conversation_id}/messages", response_class=HTMLResponse)
    async def post_message(
        conversation_id: str,
        request: Request,
        content: str = Form(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        message = service.post_user_message(
            session, conversation=conversation, user_id=user.id, content=content
        )
        from vocab.practice.usage import process_message_usage

        await process_message_usage(
            session,
            user_id=user.id,
            conversation_id=conversation.id,
            message=message,
            settings=settings,
        )
        return templates.TemplateResponse(
            request,
            "conversation/_user_turn.html",
            {
                "user": user,
                "conversation": conversation,
                "message": message,
            },
        )

    @router.get("/conversations/{conversation_id}/messages/{message_id}/partner")
    async def partner_sse(
        conversation_id: str,
        message_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> EventSourceResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        history = service.chat_history(session, conversation.id)
        topic = conversation.title
        from vocab.practice.srs import due_words as due_word_list

        due = due_word_list(session, user.id, limit=3)
        # Capture ids before the generator; the request session may close.
        conv_id = conversation.id
        uid = user.id

        async def event_gen():  # noqa: ANN202
            from vocab.llm.client import stream

            chunks: list[str] = []
            try:
                # Reuse the request session so tests and prod hit the same DB.
                async for chunk in stream(
                    "partner",
                    {"topic": topic, "due_words": due},
                    user_id=uid,
                    history=history,
                    session=session,
                    settings=settings,
                ):
                    chunks.append(chunk)
                    yield ServerSentEvent(data=html.escape(chunk), event="token")
                full = "".join(chunks).strip() or "(no reply)"
                service.save_partner_message(
                    session,
                    conversation_id=conv_id,
                    user_id=uid,
                    content=full,
                )
                yield ServerSentEvent(
                    data=html.escape(full),
                    event="done",
                )
            except Exception as exc:
                logger.exception("partner stream failed")
                yield ServerSentEvent(
                    data=html.escape(f"Partner reply failed: {exc}"),
                    event="error",
                )

        return EventSourceResponse(event_gen())

    @router.get(
        "/conversations/{conversation_id}/messages/{message_id}/feedback",
        response_class=HTMLResponse,
    )
    async def feedback_panel(
        conversation_id: str,
        message_id: str,
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        message = session.get(Message, message_id)
        if message is None or message.conversation_id != conversation.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", message)

        partner_previous = service.previous_partner_content(session, conversation.id)
        # Exclude the partner message that might not exist yet; use prior partner.
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
            return templates.TemplateResponse(
                request,
                "conversation/_feedback.html",
                {
                    "user": user,
                    "message": message,
                    "suggestions": [],
                    "failed": True,
                    "highlighted_html": "",
                },
            )

        return templates.TemplateResponse(
            request,
            "conversation/_feedback.html",
            {
                "user": user,
                "message": message,
                "suggestions": suggestions,
                "failed": False,
                "highlighted_html": highlight_message(message.content, suggestions),
            },
        )

    @router.post(
        "/conversations/{conversation_id}/suggestions/{suggestion_id}/accept",
        response_class=HTMLResponse,
    )
    def accept(
        conversation_id: str,
        suggestion_id: str,
        request: Request,
        option_id: str = Form(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if suggestion is None or suggestion.user_id != user.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        option = session.get(SuggestionOption, option_id)
        if option is None or option.suggestion_id != suggestion.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        service.accept_suggestion(session, suggestion=suggestion, option=option, user_id=user.id)
        return templates.TemplateResponse(
            request,
            "conversation/_suggestion_result.html",
            {
                "user": user,
                "conversation": conversation,
                "suggestion": suggestion,
                "accepted_word": option.word,
                "dismissed": False,
            },
        )

    @router.post(
        "/conversations/{conversation_id}/suggestions/{suggestion_id}/dismiss",
        response_class=HTMLResponse,
    )
    def dismiss(
        conversation_id: str,
        suggestion_id: str,
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        conversation = _load_owned_conversation(session, conversation_id, user)
        suggestion = session.get(Suggestion, suggestion_id)
        if suggestion is None or suggestion.user_id != user.id:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", suggestion)
        service.dismiss_suggestion(session, suggestion=suggestion, user_id=user.id)
        return templates.TemplateResponse(
            request,
            "conversation/_suggestion_result.html",
            {
                "user": user,
                "conversation": conversation,
                "suggestion": suggestion,
                "accepted_word": None,
                "dismissed": True,
            },
        )

    return router
