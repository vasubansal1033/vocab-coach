"""Helpers to send browsers from legacy HTML paths into the React HashRouter SPA."""

from __future__ import annotations

from fastapi.responses import RedirectResponse


def spa_redirect(hash_path: str) -> RedirectResponse:
    """Redirect to `/#/...` so HashRouter owns the product UI."""
    path = hash_path if hash_path.startswith("/") else f"/{hash_path}"
    return RedirectResponse(url=f"/#{path}", status_code=303)
