"""Account export and deletion endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from vocab.account.service import delete_user, export_user
from vocab.auth.deps import SESSION_KEY, current_user
from vocab.auth.models import User
from vocab.db import get_session

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/account/export")
    def account_export(
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> JSONResponse:
        payload = export_user(session, user.id)
        return JSONResponse(
            payload,
            headers={"Content-Disposition": 'attachment; filename="vocab-export.json"'},
        )

    @router.get("/account", response_class=HTMLResponse)
    def account_page(
        request: Request,
        user: User = Depends(current_user),
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "account/index.html",
            {"user": user},
        )

    @router.post("/account/delete")
    def account_delete(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        delete_user(session, user.id)
        request.session.clear()
        # Drop the key explicitly in case clear is a no-op in tests.
        request.session.pop(SESSION_KEY, None)
        return RedirectResponse(url="/auth/logout", status_code=303)

    return router
