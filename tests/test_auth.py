import re
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.auth.authorize import authorize
from vocab.auth.deps import current_user
from vocab.auth.models import Identity, User
from vocab.auth.service import get_or_create_user

ISSUER = "http://localhost:9000/application/o/vocab-coach/"


def _counts(session: Session) -> tuple[int, int]:
    users = session.scalar(select(func.count()).select_from(User))
    identities = session.scalar(select(func.count()).select_from(Identity))
    return users, identities


def test_first_login_creates_one_user_and_one_identity(session: Session) -> None:
    user = get_or_create_user(
        session, issuer=ISSUER, subject="abc", display_name="Ada", email="ada@example.com"
    )
    assert _counts(session) == (1, 1)
    assert user.display_name == "Ada"


def test_second_login_creates_nothing_more(session: Session) -> None:
    first = get_or_create_user(session, issuer=ISSUER, subject="abc")
    again = get_or_create_user(session, issuer=ISSUER, subject="abc", display_name="Changed")
    assert again.id == first.id
    assert again.display_name == ""
    assert _counts(session) == (1, 1)


def test_same_subject_from_another_issuer_is_another_user(session: Session) -> None:
    a = get_or_create_user(session, issuer=ISSUER, subject="abc")
    b = get_or_create_user(session, issuer="https://other.example/", subject="abc")
    assert a.id != b.id


def test_user_a_gets_404_for_user_b_resource(app: FastAPI, session: Session, make_user) -> None:
    a, b = make_user("A"), make_user("B")

    class Note:
        """Stand-in for any per-user resource."""

        def __init__(self, user_id: str) -> None:
            self.user_id = user_id

    notes = {"b-note": Note(b.id), "a-note": Note(a.id)}

    @app.get("/_test/notes/{note_id}")
    def read_note(note_id: str, user: User = Depends(current_user)) -> dict[str, str]:
        note = notes.get(note_id)
        if note is None:
            raise HTTPException(status_code=404)
        authorize(user.id, "read", note)
        return {"id": note_id}

    client = TestClient(app, follow_redirects=False)
    client.get(f"/_test/session/{a.id}")
    assert client.get("/_test/notes/a-note").status_code == 200
    assert client.get("/_test/notes/b-note").status_code == 404
    # Same answer as a note that does not exist, so IDs are not confirmed.
    assert client.get("/_test/notes/nope").status_code == 404


def test_anonymous_page_request_redirects_to_login(client: TestClient) -> None:
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_anonymous_htmx_request_gets_401(client: TestClient) -> None:
    assert client.get("/", headers={"HX-Request": "true"}).status_code == 401


def test_anonymous_json_request_gets_401(client: TestClient) -> None:
    assert client.get("/", headers={"accept": "application/json"}).status_code == 401


def test_session_cookie_logs_in(client: TestClient, make_user) -> None:
    user = make_user("Grace")
    client.get(f"/_test/session/{user.id}")
    response = client.get("/")
    assert response.status_code == 200
    me = client.get("/api/me", headers={"accept": "application/json"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Grace"


def test_deleted_user_is_logged_out(client: TestClient, session: Session, make_user) -> None:
    from datetime import UTC, datetime

    user = make_user()
    client.get(f"/_test/session/{user.id}")
    user.deleted_at = datetime.now(UTC)
    session.commit()
    assert client.get("/", headers={"accept": "text/html"}).status_code == 303


def test_session_cookie_is_named_vocab_session(client: TestClient, make_user) -> None:
    user = make_user()
    response = client.get(f"/_test/session/{user.id}")
    assert "vocab_session" in response.headers["set-cookie"]


def test_no_auth_bypass_in_source() -> None:
    """Only tests may override dependencies; nothing under src/ may."""
    src = Path(__file__).parent.parent / "src"
    offenders = [
        str(path)
        for path in src.rglob("*.py")
        if re.search(r"dependency_overrides", path.read_text())
    ]
    assert offenders == []


def test_provider_error_on_callback_is_a_400_not_a_crash(client: TestClient) -> None:
    response = client.get("/auth/callback?error=invalid_request&state=x")
    assert response.status_code == 400
    assert "invalid_request" in response.text
