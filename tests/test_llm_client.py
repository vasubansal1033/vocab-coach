"""Unit tests for the LLM client: retry, schema fallback, FakeLLM."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.config import Settings
from vocab.llm.client import complete, use_fake
from vocab.llm.fake import FakeLLM
from vocab.llm.models import LlmCall


class TinyOut(BaseModel):
    value: int


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    path = tmp_path / "editor.v1.md"
    path.write_text("Return JSON for {{ topic }}.", encoding="utf-8")
    return tmp_path


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        session_secret="test",
        llm_editor_model="ollama_chat/test-model",
        llm_editor_prompt_version=1,
    )


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.mark.asyncio
async def test_invalid_json_retries_once_then_records_failure(
    session: Session,
    prompts_dir: Path,
    settings: Settings,
) -> None:
    fake = FakeLLM(
        fixtures={
            "editor": [
                "not-json",
                '{"value": "still-bad"}',
            ]
        }
    )
    use_fake(fake)

    with pytest.raises(ValidationError):
        await complete(
            "editor",
            {"topic": "x"},
            output_model=TinyOut,
            session=session,
            settings=settings,
            prompts_dir=prompts_dir,
        )

    assert len(fake.calls) == 2
    rows = list(session.scalars(select(LlmCall)))
    assert len(rows) == 1
    assert rows[0].status == "error"
    assert rows[0].role == "editor"
    assert rows[0].prompt_id == "editor"
    assert rows[0].error


@pytest.mark.asyncio
async def test_json_object_fallback_when_schema_unsupported(
    session: Session,
    prompts_dir: Path,
    settings: Settings,
) -> None:
    fake = FakeLLM(fixtures={"editor": '{"value": 7}'})
    use_fake(fake)

    with patch("vocab.llm.client._supports_schema", return_value=False):
        result = await complete(
            "editor",
            {"topic": "x"},
            output_model=TinyOut,
            session=session,
            settings=settings,
            prompts_dir=prompts_dir,
        )

    assert result == TinyOut(value=7)
    assert len(fake.calls) == 1
    assert fake.calls[0]["response_format"] == {"type": "json_object"}
    system = fake.calls[0]["messages"][0]["content"]
    assert "schema" in system.lower()
    rows = list(session.scalars(select(LlmCall)))
    assert len(rows) == 1
    assert rows[0].status == "ok"
