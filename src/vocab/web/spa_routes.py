"""Legacy HTML page paths redirect into the React HashRouter SPA."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.web.spa import spa_redirect


def build_router() -> APIRouter:
    """One router for all product-page redirects (SPA owns the UI)."""
    router = APIRouter()

    @router.get("/conversations")
    def conversations(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations")

    @router.get("/conversations/new")
    def conversations_new(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations/new")

    @router.post("/conversations/new")
    def conversations_new_post(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/conversations/new")

    @router.get("/conversations/{conversation_id}")
    def conversation_detail(
        conversation_id: str, user: User = Depends(current_user)
    ) -> RedirectResponse:
        _ = user
        return spa_redirect(f"/conversations/{conversation_id}")

    @router.get("/dashboard")
    def dashboard(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/dashboard")

    @router.get("/dashboard/lemma/{lemma}")
    def dashboard_lemma(lemma: str, user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect(f"/dashboard/lemma/{lemma}")

    @router.get("/review")
    def review(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/review")

    @router.get("/drills")
    def drills(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/drills")

    @router.get("/drills/{drill_id}")
    def drill_detail(drill_id: str, user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        _ = drill_id
        return spa_redirect("/drills")

    @router.get("/account")
    def account(user: User = Depends(current_user)) -> RedirectResponse:
        _ = user
        return spa_redirect("/account")

    return router
