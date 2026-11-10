"""Only vocab.llm may import litellm or LangGraph."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "vocab"

_BLOCKED = (
    "litellm",
    "langgraph",
    "langchain",
    "langchain_core",
)


def _is_blocked(name: str) -> bool:
    return any(name == pkg or name.startswith(f"{pkg}.") for pkg in _BLOCKED)


def test_only_llm_package_imports_llm_stack() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        if "llm" in path.relative_to(SRC).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_blocked(alias.name):
                        offenders.append(str(path.relative_to(SRC)))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if _is_blocked(mod):
                    offenders.append(str(path.relative_to(SRC)))
    assert offenders == []
