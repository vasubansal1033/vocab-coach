"""Admin pages for draft groups and the review queue."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.db import get_session
from vocab.lexicon import service

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def require_admin(user: User, settings: Settings) -> None:
    """404 for non-admins so the admin surface is not advertised."""
    if not settings.admin_user_id or user.id != settings.admin_user_id:
        raise HTTPException(status_code=404, detail="Not found")


def build_router(settings: Settings | None = None) -> APIRouter:
    """Admin lexicon routes; settings captured for the admin check."""
    settings = settings or get_settings()
    router = APIRouter(prefix="/admin/lexicon")

    @router.get("", response_class=HTMLResponse)
    def lexicon_admin(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        require_admin(user, settings)
        return templates.TemplateResponse(
            request,
            "admin/lexicon.html",
            {
                "user": user,
                "drafts": service.list_drafts(session),
                "approved": service.list_approved(session),
                "queue": service.list_review_queue(session),
            },
        )

    @router.post("/groups/{group_id}/approve")
    def approve_group(
        group_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        require_admin(user, settings)
        try:
            service.approve_group(session, group_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return RedirectResponse(url="/admin/lexicon", status_code=303)

    @router.post("/groups/{group_id}/reject")
    def reject_group(
        group_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        require_admin(user, settings)
        try:
            service.reject_group(session, group_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return RedirectResponse(url="/admin/lexicon", status_code=303)

    @router.post("/groups/{group_id}/edit")
    def edit_group(
        group_id: str,
        sense_gloss: str = Form(...),
        options_blob: str = Form(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        """options_blob lines: word | distinction | example | register"""
        require_admin(user, settings)
        options: list[dict[str, str]] = []
        for line in options_blob.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            while len(parts) < 4:
                parts.append("")
            options.append(
                {
                    "word": parts[0],
                    "distinction": parts[1],
                    "example": parts[2],
                    "register": parts[3] or "neutral",
                }
            )
        try:
            service.update_group(session, group_id, sense_gloss=sense_gloss, options=options)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return RedirectResponse(url="/admin/lexicon", status_code=303)

    @router.post("/queue/{item_id}/approve")
    def approve_queue(
        item_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        require_admin(user, settings)
        try:
            service.approve_review_item(session, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return RedirectResponse(url="/admin/lexicon", status_code=303)

    @router.post("/queue/{item_id}/reject")
    def reject_queue(
        item_id: str,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        require_admin(user, settings)
        try:
            service.reject_review_item(session, item_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        return RedirectResponse(url="/admin/lexicon", status_code=303)

    return router
