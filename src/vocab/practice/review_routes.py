"""Manual review page for due FSRS cards."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.db import get_session
from vocab.practice.srs import due_options, review_card

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def _cloze(example: str, word: str) -> str:
    """Blank the option word in its example sentence."""
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub("____", example, count=1)


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/review", response_class=HTMLResponse)
    def review_page(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        options = due_options(session, user.id, limit=1)
        if not options:
            return templates.TemplateResponse(
                request,
                "practice/review.html",
                {"user": user, "option": None, "cloze": None},
            )
        option = options[0]
        return templates.TemplateResponse(
            request,
            "practice/review.html",
            {
                "user": user,
                "option": option,
                "cloze": _cloze(option.example, option.word),
            },
        )

    @router.post("/review/{option_id}")
    def review_rate(
        option_id: str,
        rating: str = Form(...),
        answer: str = Form(""),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        review_card(
            session,
            user_id=user.id,
            option_id=option_id,
            rating=rating,
            source="review_page",
        )
        return RedirectResponse(url="/review", status_code=303)

    return router
