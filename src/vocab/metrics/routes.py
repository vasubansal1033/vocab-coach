"""Legacy HTML dashboard paths redirect into the React SPA."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.web.spa import spa_redirect


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/dashboard")
    def dashboard(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/dashboard")

    @router.get("/dashboard/lemma/{lemma}")
    def dashboard_lemma(lemma: str, user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect(f"/dashboard/lemma/{lemma}")

    return router
