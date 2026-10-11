"""Prompt loader returns text plus id and version."""

from pathlib import Path

from vocab.llm.prompts import render_prompt


def test_render_prompt(tmp_path: Path) -> None:
    (tmp_path / "partner.v1.md").write_text("Hello {{ name }}.", encoding="utf-8")
    rendered = render_prompt("partner", 1, {"name": "Ada"}, prompts_dir=tmp_path)
    assert rendered.text == "Hello Ada."
    assert rendered.prompt_id == "partner"
    assert rendered.prompt_version == 1
