"""Legacy HTML drill paths redirect into the React SPA."""

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

    @router.get("/drills")
    async def drills_home(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/drills")

    @router.get("/drills/{drill_id}")
    def drills_show(drill_id: str, user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        _ = drill_id
        return spa_redirect("/drills")

    return router
