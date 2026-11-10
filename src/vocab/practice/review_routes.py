"""Legacy HTML review paths redirect into the React SPA."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.web.spa import spa_redirect


def build_router() -> APIRouter:
    router = APIRouter()

    @router.get("/review")
    def review_page(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/review")

    return router
