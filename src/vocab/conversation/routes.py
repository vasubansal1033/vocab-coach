"""Legacy HTML conversation paths redirect into the React SPA."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings, get_settings
from vocab.web.spa import spa_redirect


def build_router(settings: Settings | None = None) -> APIRouter:
    _ = settings or get_settings()
    router = APIRouter()

    @router.get("/conversations")
    def conversation_list(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations")

    @router.get("/conversations/new")
    def new_conversation_form(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations/new")

    @router.post("/conversations/new")
    def new_conversation(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations/new")

    @router.get("/conversations/{conversation_id}")
    def conversation_view(
        conversation_id: str, user: User = Depends(current_user)
    ) -> RedirectResponse:
        _ = user
        return spa_redirect(f"/conversations/{conversation_id}")

    return router
