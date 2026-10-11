"""Only vocab.llm may import litellm."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "vocab"


def test_only_llm_package_imports_litellm() -> None:
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        if "llm" in path.relative_to(SRC).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "litellm" or alias.name.startswith("litellm."):
                        offenders.append(str(path.relative_to(SRC)))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "litellm" or mod.startswith("litellm."):
                    offenders.append(str(path.relative_to(SRC)))
    assert offenders == []
