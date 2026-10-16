"""Lexicon load, approve, and admin gate."""

from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.db import get_session
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
from vocab.lexicon.service import (
    approve_group,
    approved_groups_for_lemma,
    counts,
    load_seeds,
)
from vocab.main import create_app


def test_load_seeds_twice_same_counts(session: Session) -> None:
    first = load_seeds(session)
    mid = counts(session)
    second = load_seeds(session)
    end = counts(session)
    assert first["groups"] == second["groups"]
    assert first["options"] == second["options"]
    assert mid == end
    assert end["groups"] >= 10
    assert end["options"] >= 30


def test_approve_draft_visible_by_lemma(session: Session) -> None:
    session.add(
        PrecisionGroup(
            id="fix.extra",
            head_lemma="fix",
            pos="VERB",
            sense_gloss="another repair sense",
            status="draft",
            source="llm",
        )
    )
    session.add(
        PrecisionOption(
            id="fix.extra/remedy",
            group_id="fix.extra",
            word="remedy",
            distinction="corrects an undesirable state",
            example="We remedied the gap with a backfill.",
            register="formal",
            status="draft",
        )
    )
    session.commit()

    assert approved_groups_for_lemma(session, "fix") == []
    approve_group(session, "fix.extra")
    groups = approved_groups_for_lemma(session, "fix")
    assert len(groups) == 1
    assert groups[0].id == "fix.extra"
    assert groups[0].options[0].word == "remedy"


def test_admin_lexicon_requires_admin_user(
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

    app.dependency_overrides[current_user] = lambda: other
    assert client.get("/admin/lexicon").status_code == 404

    app.dependency_overrides[current_user] = lambda: admin
    assert client.get("/admin/lexicon").status_code == 200
