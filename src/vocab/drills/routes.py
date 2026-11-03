"""Drill pages: show sentence, collect rewrite, show grade."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vocab.auth.authorize import authorize
from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.db import get_session
from vocab.drills.models import Drill
from vocab.drills.service import create_drill, grade_attempt

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def build_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or get_settings()
    router = APIRouter()

    @router.get("/drills", response_class=HTMLResponse)
    async def drills_home(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        drill = await create_drill(session, user_id=user.id, settings=settings)
        return templates.TemplateResponse(
            request,
            "drills/show.html",
            {"user": user, "drill": drill, "attempt": None},
        )

    @router.get("/drills/{drill_id}", response_class=HTMLResponse)
    def show_drill(
        drill_id: str,
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        drill = session.get(Drill, drill_id)
        if drill is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "read", drill)
        return templates.TemplateResponse(
            request,
            "drills/show.html",
            {"user": user, "drill": drill, "attempt": None},
        )

    @router.post("/drills/{drill_id}/attempt", response_class=HTMLResponse)
    async def submit_attempt(
        drill_id: str,
        request: Request,
        answer: str = Form(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        drill = session.get(Drill, drill_id)
        if drill is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")
        authorize(user.id, "update", drill)
        attempt = await grade_attempt(
            session,
            drill=drill,
            user_id=user.id,
            answer=answer,
            settings=settings,
        )
        return templates.TemplateResponse(
            request,
            "drills/show.html",
            {"user": user, "drill": drill, "attempt": attempt},
        )

    @router.post("/drills/next")
    async def next_drill(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        drill = await create_drill(session, user_id=user.id, settings=settings)
        return RedirectResponse(url=f"/drills/{drill.id}", status_code=303)

    return router
