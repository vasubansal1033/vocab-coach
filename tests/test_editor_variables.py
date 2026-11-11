"""Editor prompt variables include synonym hints and lexicon matches."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.editor.service import build_editor_variables
from vocab.lexicon.service import load_seeds
from vocab.nlp.analyzer import analyze


@pytest.mark.asyncio
async def test_build_editor_variables_includes_hints(
    session: Session,
    make_user: Callable[..., User],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = make_user
    load_seeds(session)

    async def fake_hints(
        lemmas: list[tuple[str, str | None]],
        *,
        timeout: float = 2.0,
    ) -> dict[str, list[str]]:
        _ = lemmas, timeout
        return {"fix": ["resolve", "mitigate", "remediate"]}

    monkeypatch.setattr("vocab.editor.service.synonym_hints", fake_hints)
    text = "We need to fix the bug."
    variables = await build_editor_variables(
        session,
        message=text,
        analysis=analyze(text),
    )
    assert variables["synonym_hints"]["fix"] == ["resolve", "mitigate", "remediate"]
    group_ids = {g["id"] for g in variables["groups"]}
    assert "fix.repair" in group_ids
