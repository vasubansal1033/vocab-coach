"""Dashboard metrics: hand-calculated fixture + MTLD unit cases."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from fastapi.testclient import TestClient
from metrics_fixture import ANCHOR, WINDOW_START, seed_metrics_fixture
from sqlalchemy.orm import Session
from wordfreq import word_frequency

from vocab.auth.models import User
from vocab.metrics.lexical import mtld
from vocab.metrics.queries import (
    acceptance_rate,
    crutch_rate,
    crutch_rate_for_lemma,
    crutch_rate_weekly,
    drill_score_weekly,
    lexical_diversity,
    misuse_rate,
    overuse_lift,
    spontaneous_correct_use,
)


def test_mtld_none_below_100_words() -> None:
    assert mtld(["cat", "dog"] * 40) is None  # 80 tokens


def test_mtld_hand_calculated_alternating() -> None:
    """102 tokens of cat/dog: TTR hits 0.72 every 3 tokens → MTLD = 3.0 both ways."""
    tokens = ["cat", "dog"] * 51
    assert len(tokens) == 102
    assert mtld(tokens) == 3.0


def test_fixture_metrics(session: Session, make_user: Callable[..., User]) -> None:
    user = make_user()
    seed_metrics_fixture(session, user)
    start, end = WINDOW_START, ANCHOR

    assert crutch_rate(session, user.id, start, end) == 500.0
    assert crutch_rate_for_lemma(session, user.id, start, end, "fix") == 150.0

    weekly = crutch_rate_weekly(session, user.id, start, end)
    assert [(w.label, w.rate) for w in weekly] == [
        ((ANCHOR - timedelta(days=7)).date().isoformat(), 600.0),
        (ANCHOR.date().isoformat(), 400.0),
    ]

    freq = word_frequency("thing", "en")
    expected_lift = (5 / 20) / freq
    lifts = overuse_lift(session, user.id, start, end, limit=10)
    thing = next(row for row in lifts if row.word == "thing")
    assert thing.uses == 5
    assert abs(thing.lift - expected_lift) < 1e-9
    assert any(g.id.startswith("thing.") for g in thing.groups)

    assert acceptance_rate(session, user.id, start, end) == 0.5
    assert (
        acceptance_rate(
            session,
            user.id,
            start,
            end,
            prompt_version=1,
            model="test-editor",
        )
        == 0.5
    )
    assert (
        acceptance_rate(
            session,
            user.id,
            start,
            end,
            prompt_version=99,
            model="test-editor",
        )
        is None
    )

    assert spontaneous_correct_use(session, user.id, start, end) == 0.5
    assert abs(misuse_rate(session, user.id, start, end) - (1 / 3)) < 1e-12

    drills = drill_score_weekly(session, user.id, start, end)
    assert [(w.label, w.score) for w in drills] == [
        ((ANCHOR - timedelta(days=7)).date().isoformat(), 3.0),
        (ANCHOR.date().isoformat(), 5.0),
    ]

    # Fixture has 20 words → diversity withheld.
    assert lexical_diversity(session, user.id, start, end) is None


def test_dashboard_pages(
    client: TestClient,
    session: Session,
    make_user: Callable[..., User],
    login_as: Callable[[User], None],
) -> None:
    user = make_user()
    seed_metrics_fixture(session, user)
    login_as(user)
    home = client.get("/dashboard")
    assert home.status_code == 200
    assert b"Crutch rate" in home.content
    assert b"chart.umd.min.js" in home.content
    lemma = client.get("/dashboard/lemma/fix")
    assert lemma.status_code == 200
    assert b"fix" in lemma.content
