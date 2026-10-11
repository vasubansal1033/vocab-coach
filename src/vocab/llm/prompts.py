"""Load and render versioned prompt Markdown files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from vocab.llm.roles import Role

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_env = Environment(undefined=StrictUndefined, autoescape=False)


@dataclass(frozen=True)
class RenderedPrompt:
    """Rendered prompt text plus the ids stored on llm_calls."""

    text: str
    prompt_id: str
    prompt_version: int


def render_prompt(
    role: Role,
    version: int,
    variables: dict[str, Any],
    *,
    prompts_dir: Path | None = None,
) -> RenderedPrompt:
    """Render `prompts/<role>.v<N>.md`; never edit a file that has recorded data."""
    directory = prompts_dir or PROMPTS_DIR
    path = directory / f"{role}.v{version}.md"
    if not path.is_file():
        raise FileNotFoundError(f"prompt file missing: {path}")
    template = _env.from_string(path.read_text(encoding="utf-8"))
    text = template.render(**variables)
    return RenderedPrompt(text=text, prompt_id=role, prompt_version=version)
