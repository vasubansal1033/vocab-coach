"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from vocab.account.routes import build_router as build_account_router
from vocab.api.routes import build_router as build_api_router
from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.auth.oidc import build_router
from vocab.config import Settings, get_settings
from vocab.lexicon.admin import build_router as build_lexicon_admin
from vocab.nlp.model import load as load_nlp
from vocab.web.spa_routes import build_router as build_spa_redirect_router

WEB_DIR = Path(__file__).parent / "web"
SPA_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SPA_ASSETS = SPA_DIR / "assets"
templates = Jinja2Templates(directory=WEB_DIR / "templates")


SESSION_MAX_AGE = 14 * 24 * 3600


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Load spaCy once at startup so requests do not pay the model cost."""
    load_nlp()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app; a factory keeps tests free of shared state."""
    settings = settings or get_settings()
    if not settings.session_secret:
        raise RuntimeError("SESSION_SECRET is empty; set it in .env (openssl rand -hex 32)")
    app = FastAPI(title="vocab-coach", lifespan=lifespan)
    # Distinct cookie name: browsers share cookies across ports on localhost.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="vocab_session",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.app_env == "prod",
    )
    app.include_router(build_router(settings))
    app.include_router(build_api_router(settings))
    app.include_router(build_account_router())
    app.include_router(build_spa_redirect_router())
    app.include_router(build_lexicon_admin(settings))
    app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
    if SPA_ASSETS.is_dir():
        app.mount("/assets", StaticFiles(directory=SPA_ASSETS), name="spa_assets")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def index(request: Request, user: User = Depends(current_user)) -> Response:
        spa_index = SPA_DIR / "index.html"
        if spa_index.is_file():
            return FileResponse(spa_index)
        return templates.TemplateResponse(request, "index.html", {"user": user})

    @app.get("/about/attribution")
    def attribution(request: Request) -> Response:
        return templates.TemplateResponse(request, "about/attribution.html", {})

    @app.get("/about/privacy")
    def privacy(request: Request) -> Response:
        return templates.TemplateResponse(
            request,
            "about/privacy.html",
            {"privacy_note": settings.llm_privacy_note},
        )

    return app


app = create_app()
