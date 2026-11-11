"""Paginated lexicon list and idempotent user batch ingest."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from lexicon_fixture import seed_lexicon
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.db import get_session
from vocab.lexicon.models import LexiconSubmission, PrecisionGroup
from vocab.main import create_app


def test_lexicon_list_and_detail_paginated(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    seed_lexicon(session)
    user = make_user()
    login_as(user)

    first = client.get(
        "/api/lexicon/groups",
        params={"kind": "precision", "limit": 2},
        headers={"accept": "application/json"},
    )
    assert first.status_code == 200
    body = first.json()
    assert len(body["groups"]) == 2
    assert body["next_cursor"] is not None

    second = client.get(
        "/api/lexicon/groups",
        params={"kind": "precision", "limit": 2, "cursor": body["next_cursor"]},
        headers={"accept": "application/json"},
    )
    assert second.status_code == 200
    assert second.json()["groups"][0]["id"] > body["groups"][-1]["id"]

    detail = client.get(
        f"/api/lexicon/groups/{body['groups'][0]['id']}",
        headers={"accept": "application/json"},
    )
    assert detail.status_code == 200
    assert detail.json()["options"]


def test_lexicon_submit_idempotent(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user()
    login_as(user)
    payload = {
        "items": [
            {
                "kind": "precision",
                "head_lemma": "vague",
                "groups": [
                    {
                        "id": "vague.unclear",
                        "pos": "ADJ",
                        "sense_gloss": "not specific enough",
                        "options": [
                            {
                                "word": "ambiguous",
                                "distinction": "more than one reading",
                                "example": "The brief is ambiguous.",
                                "register": "neutral",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    headers = {
        "accept": "application/json",
        "Idempotency-Key": "batch-1",
    }
    created = client.post("/api/lexicon/submissions", json=payload, headers=headers)
    assert created.status_code == 200
    first = created.json()
    assert first["count"] == 1
    assert first["created"][0]["status"] == "draft"
    stored_id = first["created"][0]["stored_id"]
    group = session.get(PrecisionGroup, stored_id)
    assert group is not None
    assert group.source == "user"
    assert group.status == "draft"

    replay = client.post("/api/lexicon/submissions", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == first
    from sqlalchemy import func, select

    n = session.scalar(
        select(func.count())
        .select_from(LexiconSubmission)
        .where(
            LexiconSubmission.user_id == user.id,
            LexiconSubmission.idempotency_key == "batch-1",
        )
    )
    assert n == 1

    conflict = client.post(
        "/api/lexicon/submissions",
        json={
            "items": [
                {
                    "kind": "precision",
                    "head_lemma": "other",
                    "groups": [
                        {
                            "id": "other.sense",
                            "pos": "NOUN",
                            "sense_gloss": "different body",
                            "options": [
                                {
                                    "word": "elsewhere",
                                    "distinction": "not here",
                                    "example": "Try elsewhere.",
                                }
                            ],
                        }
                    ],
                }
            ]
        },
        headers=headers,
    )
    assert conflict.status_code == 409


def test_lexicon_submit_does_not_overwrite_approved(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    from sqlalchemy import select

    seed_lexicon(session)
    user = make_user()
    login_as(user)
    approved_id = session.scalars(
        select(PrecisionGroup.id).where(PrecisionGroup.status == "approved").limit(1)
    ).first()
    assert approved_id
    payload = {
        "items": [
            {
                "kind": "precision",
                "head_lemma": "fix",
                "groups": [
                    {
                        "id": approved_id,
                        "pos": "VERB",
                        "sense_gloss": "user attempt to overwrite",
                        "options": [
                            {
                                "word": "userword",
                                "distinction": "should stay draft under new id",
                                "example": "We userworded it.",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    res = client.post(
        "/api/lexicon/submissions",
        json=payload,
        headers={"accept": "application/json", "Idempotency-Key": "no-clobber"},
    )
    assert res.status_code == 200
    stored = res.json()["created"][0]["stored_id"]
    assert stored != approved_id
    assert session.get(PrecisionGroup, approved_id).status == "approved"
    assert session.get(PrecisionGroup, stored).status == "draft"


def test_admin_import_json_and_builtin(
    session: Session,
    make_user: Callable[..., User],
) -> None:
    admin = make_user("Admin")
    other = make_user("Other")
    app = create_app(
        Settings(
            _env_file=None,
            session_secret="test-session-secret",
            admin_user_id=admin.id,
        )
    )
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app, follow_redirects=False)

    payload = {
        "items": [
            {
                "kind": "precision",
                "head_lemma": "seed",
                "groups": [
                    {
                        "id": "seed.api",
                        "pos": "NOUN",
                        "sense_gloss": "imported via admin API",
                        "options": [
                            {
                                "word": "nucleus",
                                "distinction": "central part",
                                "example": "The nucleus of the plan.",
                                "register": "neutral",
                            }
                        ],
                    }
                ],
            }
        ]
    }
    headers = {"accept": "application/json", "Idempotency-Key": "admin-import-1"}

    app.dependency_overrides[current_user] = lambda: other
    assert client.post("/api/lexicon/import", json=payload, headers=headers).status_code == 404
    assert client.post("/api/lexicon/import/builtin").status_code == 404

    app.dependency_overrides[current_user] = lambda: admin
    imported = client.post("/api/lexicon/import", json=payload, headers=headers)
    assert imported.status_code == 200
    body = imported.json()
    assert body["mode"] == "approved"
    assert body["groups"] == 1
    group = session.get(PrecisionGroup, "seed.api")
    assert group is not None
    assert group.status == "approved"
    assert group.source == "api"

    replay = client.post("/api/lexicon/import", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == body

    builtin = client.post("/api/lexicon/import/builtin")
    assert builtin.status_code == 200
    counts = builtin.json()
    assert counts["groups"] >= 10
    assert counts["options"] >= 30
    assert session.get(PrecisionGroup, "confusable.imply-infer") is not None
    assert session.get(PrecisionGroup, "idiom.agree") is not None
