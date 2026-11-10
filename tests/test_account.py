"""Account export and deletion."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.auth.models import Identity, User
from vocab.conversation.models import Conversation
from vocab.events import Event


def test_export_and_delete(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user("Ada")
    session.add(Identity(user_id=user.id, issuer="https://idp.example/", subject="sub-1"))
    session.add(Conversation(user_id=user.id, title="Ship review"))
    session.add(
        Event(
            user_id=user.id,
            type="suggestion_dismissed",
            subject_type="suggestion",
            subject_id="sug-x",
            payload={},
        )
    )
    session.commit()
    login_as(user)

    exported = client.get("/account/export")
    assert exported.status_code == 200
    body = exported.json()
    assert body["user"]["id"] == user.id
    assert len(body["conversations"]) == 1
    assert len(body["events"]) == 1

    deleted = client.post("/account/delete", follow_redirects=False)
    assert deleted.status_code == 303
    assert session.get(User, user.id) is None
    left = session.scalars(select(Conversation).where(Conversation.user_id == user.id)).first()
    assert left is None
    assert session.scalars(select(Identity).where(Identity.user_id == user.id)).first() is None
