"""Public dataset converters and admin import endpoint."""

from __future__ import annotations

import csv
import gzip
import io
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.db import get_session
from vocab.lexicon.ingest import import_public_catalog
from vocab.lexicon.models import PrecisionGroup
from vocab.lexicon.public_datasets import (
    abc_precision_to_items,
    abc_vs_notes_to_items,
    lexkite_to_items,
)
from vocab.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "public_lexicon"


def test_lexkite_and_abc_converters() -> None:
    payload = json.loads((FIXTURES / "confused-words.json").read_text(encoding="utf-8"))
    lexkite = lexkite_to_items(payload)
    assert len(lexkite) == 1
    assert lexkite[0].kind == "confusable"
    assert lexkite[0].groups[0].id.startswith("confusable.lexkite.")
    assert len(lexkite[0].groups[0].options) == 2

    rows = [
        json.loads(line)
        for line in gzip.decompress((FIXTURES / "abcthesaurus-en.jsonl.gz").read_bytes())
        .decode()
        .splitlines()
        if line.strip()
    ]
    precision = abc_precision_to_items(rows, lemmas={"good"})
    assert len(precision) == 1
    assert precision[0].head_lemma == "good"
    assert precision[0].groups[0].id.startswith("good.abc.")
    assert len(precision[0].groups[0].options) >= 2

    raw = gzip.decompress((FIXTURES / "abcthesaurus-vs-notes.csv.gz").read_bytes()).decode()
    notes = list(csv.DictReader(io.StringIO(raw)))
    confusable = abc_vs_notes_to_items(notes)
    assert len(confusable) == 1
    assert confusable[0].groups[0].id.startswith("confusable.abc.")


def test_import_public_catalog_from_fixtures(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vocab.lexicon.public_datasets as public

    def fake_download(url: str, *, filename: str, timeout: float = 120.0) -> Path:
        mapping = {
            "confused-words.json": FIXTURES / "confused-words.json",
            "abcthesaurus-en.jsonl.gz": FIXTURES / "abcthesaurus-en.jsonl.gz",
            "abcthesaurus-vs-notes.csv.gz": FIXTURES / "abcthesaurus-vs-notes.csv.gz",
        }
        return mapping[filename]

    monkeypatch.setattr(public, "_download", fake_download)
    result = import_public_catalog(
        session,
        sources=["lexkite", "abc_precision", "abc_confusable"],
        source="public",
    )
    assert result["groups"] >= 3
    assert result["options"] >= 6
    assert session.scalar(select(func.count()).select_from(PrecisionGroup)) >= 3
    assert any("Lexkite" in line for line in result["attribution"])


def test_admin_import_public_requires_admin(
    session: Session,
    make_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vocab.lexicon.public_datasets as public

    def fake_download(url: str, *, filename: str, timeout: float = 120.0) -> Path:
        mapping = {
            "confused-words.json": FIXTURES / "confused-words.json",
            "abcthesaurus-en.jsonl.gz": FIXTURES / "abcthesaurus-en.jsonl.gz",
            "abcthesaurus-vs-notes.csv.gz": FIXTURES / "abcthesaurus-vs-notes.csv.gz",
        }
        return mapping[filename]

    monkeypatch.setattr(public, "_download", fake_download)
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
    assert (
        client.post("/api/lexicon/import/public", params={"sources": "lexkite"}).status_code == 404
    )

    app.dependency_overrides[current_user] = lambda: admin
    ok = client.post("/api/lexicon/import/public", params={"sources": "lexkite"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["groups"] >= 1
    assert "attribution" in body
