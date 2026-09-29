"""The `current_user` dependency used by every route that touches user data."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.db import get_session

SESSION_KEY = "user_id"
LOGIN_PATH = "/auth/login"


def _wants_page(request: Request) -> bool:
    """Browsers navigating to a page get a redirect; htmx and JSON clients get 401.

    A redirect to the login page is useless to an htmx swap or an API client.
    """
    if request.headers.get("HX-Request"):
        return False
    accept = request.headers.get("accept", "")
    return "application/json" not in accept or "text/html" in accept


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    """Load the user named in the session cookie, or send the caller to log in."""
    user_id = request.session.get(SESSION_KEY)
    user = session.get(User, user_id) if user_id else None
    if user is None or user.deleted_at is not None:
        request.session.clear()
        if _wants_page(request):
            raise HTTPException(status_code=303, headers={"Location": LOGIN_PATH})
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
