"""JSON API used by the React SPA."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from metrics_fixture import seed_metrics_fixture
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.lexicon.service import load_seeds


def test_api_me_and_dashboard(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user()
    seed_metrics_fixture(session, user)
    login_as(user)

    me = client.get("/api/me", headers={"accept": "application/json"})
    assert me.status_code == 200
    assert me.json()["id"] == user.id

    dash = client.get("/api/dashboard", headers={"accept": "application/json"})
    assert dash.status_code == 200
    body = dash.json()
    assert body["crutch_rate"] == 500.0
    assert body["acceptance"] == 0.5


def test_api_create_conversation(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    load_seeds(session)
    user = make_user()
    login_as(user)
    created = client.post(
        "/api/conversations",
        headers={"accept": "application/json"},
        json={"topic": "Ship review"},
    )
    assert created.status_code == 200
    conversation_id = created.json()["id"]
    listed = client.get("/api/conversations", headers={"accept": "application/json"})
    assert listed.status_code == 200
    assert any(c["id"] == conversation_id for c in listed.json()["conversations"])
