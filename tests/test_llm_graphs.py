"""LangGraph role workflows use FakeLLM the same way as direct client calls."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from vocab.config import Settings
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.llm.graphs import run_partner_stream, run_structured_role


class _Tiny(BaseModel):
    ok: bool


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    (tmp_path / "editor.v1.md").write_text("Editor for {{ message }}.", encoding="utf-8")
    (tmp_path / "partner.v1.md").write_text("Partner on {{ topic }}.", encoding="utf-8")
    return tmp_path


@pytest.mark.asyncio
async def test_structured_role_graph(prompts_dir: Path) -> None:
    use_fake(FakeLLM(fixtures={"editor": '{"ok": true}'}))
    settings = Settings(
        _env_file=None,
        session_secret="test",
        llm_editor_model="fake-editor",
        llm_editor_prompt_version=1,
    )
    result = await run_structured_role(
        "editor",
        {"message": "x"},
        output_model=_Tiny,
        settings=settings,
        prompts_dir=prompts_dir,
    )
    assert isinstance(result, _Tiny)
    assert result.ok is True


@pytest.mark.asyncio
async def test_partner_stream_graph(prompts_dir: Path) -> None:
    use_fake(
        FakeLLM(
            fixtures={"partner": "Hello"},
            stream_chunks={"partner": ["Hel", "lo"]},
        )
    )
    settings = Settings(
        _env_file=None,
        session_secret="test",
        llm_partner_model="fake-partner",
        llm_partner_prompt_version=1,
    )
    chunks: list[str] = []
    async for chunk in run_partner_stream(
        {"topic": "test", "due_words": []},
        settings=settings,
        prompts_dir=prompts_dir,
    ):
        chunks.append(chunk)
    assert "".join(chunks) == "Hello"
