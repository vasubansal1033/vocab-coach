"""Login, callback and logout against authentik using the authorization code flow."""

from authlib.integrations.base_client import OAuthError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from vocab.auth.deps import SESSION_KEY
from vocab.auth.service import get_or_create_user
from vocab.config import Settings
from vocab.db import get_session

PROVIDER = "authentik"


def build_oauth(settings: Settings) -> OAuth:
    """Register the provider from settings; discovery happens lazily on first use."""
    oauth = OAuth()
    oauth.register(
        name=PROVIDER,
        server_metadata_url=f"{settings.oidc_issuer}.well-known/openid-configuration",
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret,
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


def build_router(settings: Settings) -> APIRouter:
    """Routes close over one `OAuth` registry, so tests can build their own."""
    router = APIRouter(prefix="/auth", tags=["auth"])
    oauth = build_oauth(settings)
    client = oauth.create_client(PROVIDER)

    @router.get("/login", name="auth_login")
    async def login(request: Request) -> RedirectResponse:
        return await client.authorize_redirect(request, request.url_for("auth_callback"))

    @router.get("/callback", name="auth_callback")
    async def callback(
        request: Request, session: Session = Depends(get_session)
    ) -> RedirectResponse:
        try:
            token = await client.authorize_access_token(request)
        except OAuthError as error:
            # Provider refusals and expired state are user-facing failures, not server bugs.
            raise HTTPException(status_code=400, detail=f"Login failed: {error.error}") from error
        claims = token.get("userinfo")
        if not claims or not claims.get("iss") or not claims.get("sub"):
            raise HTTPException(status_code=400, detail="Identity provider returned no identity")
        user = get_or_create_user(
            session,
            issuer=claims["iss"],
            subject=claims["sub"],
            display_name=claims.get("name") or claims.get("preferred_username") or "",
            email=claims.get("email"),
        )
        # Only the internal id goes in the cookie: no tokens, no OIDC subject.
        request.session.clear()
        request.session[SESSION_KEY] = user.id
        return RedirectResponse("/", status_code=303)

    @router.get("/logout", name="auth_logout")
    async def logout(request: Request) -> RedirectResponse:
        """End the app session, then authentik's, so the next login asks for credentials."""
        request.session.clear()
        metadata = await client.load_server_metadata()
        end_session = metadata.get("end_session_endpoint")
        return RedirectResponse(end_session or "/", status_code=303)

    return router
