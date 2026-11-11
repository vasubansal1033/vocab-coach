"""Lexicon load, approve, kind filters, and admin gate."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.db import get_session
from vocab.editor.service import build_editor_variables
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
from vocab.lexicon.schemas import ConfusableDetails, IdiomDetails, LemmaSeedFile
from vocab.lexicon.service import (
    approve_group,
    approved_groups_for_lemma,
    counts,
    load_seeds,
)
from vocab.main import create_app
from vocab.nlp.analyzer import analyze
from vocab.nlp.types import CandidateSpan


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


def test_load_seeds_includes_confusable_and_idiom(session: Session) -> None:
    load_seeds(session)
    confusable = session.get(PrecisionGroup, "confusable.imply-infer")
    idiom = session.get(PrecisionGroup, "idiom.agree")
    assert confusable is not None
    assert confusable.kind == "confusable"
    assert confusable.head_lemma is None
    imply = session.get(PrecisionOption, "confusable.imply-infer/imply")
    assert imply is not None
    assert imply.details is not None
    assert imply.details["connotation"] == "neutral"

    assert idiom is not None
    assert idiom.kind == "idiom"
    assert idiom.head_lemma == "agree"
    eye = session.get(PrecisionOption, "idiom.agree/see eye to eye")
    assert eye is not None
    assert eye.details is not None
    assert eye.details["tier"] == "everyday"


def test_approved_groups_for_lemma_defaults_to_precision(session: Session) -> None:
    load_seeds(session)
    precision_only = approved_groups_for_lemma(session, "agree")
    assert all(g.kind == "precision" for g in precision_only)
    assert not any(g.id == "idiom.agree" for g in precision_only)

    with_idioms = approved_groups_for_lemma(session, "agree", kinds=("precision", "idiom"))
    assert any(g.id == "idiom.agree" for g in with_idioms)


@pytest.mark.asyncio
async def test_editor_variables_exclude_idiom_groups(session: Session) -> None:
    """Without allow_idioms, a message with 'agree' must not feed idiom groups."""
    load_seeds(session)
    message = "We agree on the timeline."
    analysis = analyze(message)
    # Force agree as a candidate so head-lemma lookup runs (it is not a crutch).
    analysis.candidates = [
        CandidateSpan(
            text="agree",
            start=3,
            end=8,
            lemma="agree",
            pos="VERB",
            reason="crutch",
        )
    ]
    variables = await build_editor_variables(session, message=message, analysis=analysis)
    group_ids = {g["id"] for g in variables["groups"]}
    assert "idiom.agree" not in group_ids
    assert "confusable.imply-infer" not in group_ids


def test_seed_details_validation() -> None:
    ConfusableDetails.model_validate({"collocations": ["imply that"], "connotation": "neutral"})
    IdiomDetails.model_validate(
        {
            "meaning": "share a view",
            "misuse_example": "bad",
            "avoid_when": "formal letter",
        }
    )
    with pytest.raises(ValidationError):
        LemmaSeedFile.model_validate(
            {
                "kind": "idiom",
                "head_lemma": "agree",
                "groups": [
                    {
                        "id": "idiom.agree",
                        "pos": "VERB",
                        "sense_gloss": "x",
                        "options": [
                            {
                                "word": "see eye to eye",
                                "distinction": "d",
                                "example": "e",
                                "register": "neutral",
                            }
                        ],
                    }
                ],
            }
        )


def test_approve_draft_visible_by_lemma(session: Session) -> None:
    session.add(
        PrecisionGroup(
            id="fix.extra",
            head_lemma="fix",
            kind="precision",
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

    load_seeds(session)
    app.dependency_overrides[current_user] = lambda: admin
    response = client.get("/admin/lexicon")
    assert response.status_code == 200
    assert b"confusable.imply-infer" in response.content
    assert b"idiom.agree" in response.content
    assert b"kind=confusable" in response.content
    assert b"kind=idiom" in response.content
