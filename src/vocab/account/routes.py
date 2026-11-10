"""Account page redirects into the SPA; export/delete stay as HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from vocab.account.service import delete_user, export_user
from vocab.auth.deps import SESSION_KEY, current_user
from vocab.auth.models import User
from vocab.db import get_session
from vocab.web.spa import spa_redirect


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/account")
    def account_page(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/account")

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

    @router.post("/account/delete")
    def account_delete(
        request: Request,
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        delete_user(session, user.id)
        request.session.clear()
        request.session.pop(SESSION_KEY, None)
        return RedirectResponse(url="/auth/logout", status_code=303)

    return router
