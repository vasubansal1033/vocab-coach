"""Dashboard pages built from metrics queries."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.db import get_session
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

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/dashboard", response_class=HTMLResponse)
    def dashboard(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
        prompt_version: str | None = Query(default=None),
        model: str | None = Query(default=None),
    ) -> HTMLResponse:
        start, end = default_window()
        version = int(prompt_version) if prompt_version and prompt_version.strip() else None
        model_filter = model.strip() if model and model.strip() else None
        weekly = crutch_rate_weekly(session, user.id, start, end)
        chart_labels = [w.label for w in weekly]
        chart_rates = [w.rate if w.rate is not None else 0 for w in weekly]
        drill_weeks = drill_score_weekly(session, user.id, start, end)
        return templates.TemplateResponse(
            request,
            "dashboard/index.html",
            {
                "user": user,
                "window_start": start,
                "window_end": end,
                "crutch_rate": crutch_rate(session, user.id, start, end),
                "weekly": weekly,
                "chart_labels": chart_labels,
                "chart_rates": chart_rates,
                "overuse": overuse_lift(session, user.id, start, end),
                "acceptance": acceptance_rate(
                    session,
                    user.id,
                    start,
                    end,
                    prompt_version=version,
                    model=model_filter,
                ),
                "spontaneous": spontaneous_correct_use(session, user.id, start, end),
                "misuse": misuse_rate(session, user.id, start, end),
                "drill_weeks": drill_weeks,
                "mtld": lexical_diversity(session, user.id, start, end),
                "prompt_version": version,
                "model": model_filter,
            },
        )

    @router.get("/dashboard/lemma/{lemma}", response_class=HTMLResponse)
    def dashboard_lemma(
        lemma: str,
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        start, end = default_window()
        detail = lemma_detail(session, user.id, start, end, lemma)
        return templates.TemplateResponse(
            request,
            "dashboard/lemma.html",
            {
                "user": user,
                "detail": detail,
                "window_start": start,
                "window_end": end,
            },
        )

    return router
