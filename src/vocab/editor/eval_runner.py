"""Run the editor against a gold YAML file and report quality metrics."""

from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.editor.schemas import EditorOutput
from vocab.editor.service import build_editor_variables
from vocab.lexicon.service import load_seeds
from vocab.llm.graphs import run_structured_role
from vocab.nlp.analyzer import analyze

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_PATH = REPO_ROOT / "evals" / "editor_gold.yaml"
RESULTS_DIR = REPO_ROOT / "evals" / "results"


class GoldCase(BaseModel):
    id: str
    text: str
    partner_previous: str | None = None
    must_flag: list[str] = Field(default_factory=list)
    may_flag: list[str] = Field(default_factory=list)
    must_keep: list[str] = Field(default_factory=list)
    acceptable_options: dict[str, list[str]] = Field(default_factory=dict)
    forbidden_options: list[str] = Field(default_factory=list)
    expect_empty: bool = False


def load_gold(path: Path | None = None) -> list[GoldCase]:
    raw = yaml.safe_load((path or GOLD_PATH).read_text(encoding="utf-8"))
    return [GoldCase.model_validate(item) for item in raw]


def _flagged_originals(output: EditorOutput) -> list[str]:
    return [s.original for s in output.suggestions]


def _contains_span(flagged: list[str], needle: str) -> bool:
    needle_l = needle.lower()
    for item in flagged:
        if needle_l == item.lower() or needle_l in item.lower() or item.lower() in needle_l:
            return True
    return False


async def _run_case(
    case: GoldCase,
    session: Session,
    settings: Settings,
) -> dict[str, Any]:
    analysis = analyze(case.text)
    variables = await build_editor_variables(
        session,
        message=case.text,
        analysis=analysis,
        partner_previous=case.partner_previous,
    )
    started = time.perf_counter()
    schema_failed = False
    output: EditorOutput | None = None
    error: str | None = None
    try:
        result = await run_structured_role(
            "editor",
            variables,
            output_model=EditorOutput,
            session=session,
            settings=settings,
        )
        assert isinstance(result, EditorOutput)
        output = result
    except (ValidationError, ValueError, AssertionError) as exc:
        schema_failed = True
        error = str(exc)
    latency_ms = int((time.perf_counter() - started) * 1000)

    flagged = _flagged_originals(output) if output else []
    must_hits = sum(1 for span in case.must_flag if _contains_span(flagged, span))
    must_total = len(case.must_flag)
    false_flags = sum(1 for span in case.must_keep if _contains_span(flagged, span))
    if case.expect_empty and flagged:
        false_flags += len(flagged)

    acceptable_hits = 0
    acceptable_total = 0
    inflation = 0
    if output:
        for suggestion in output.suggestions:
            allowed = case.acceptable_options.get(suggestion.original, [])
            # Also try matching keys loosely.
            if not allowed:
                for key, words in case.acceptable_options.items():
                    if _contains_span([suggestion.original], key):
                        allowed = words
                        break
            for opt in suggestion.options:
                if allowed:
                    acceptable_total += 1
                    if opt.word.lower() in {w.lower() for w in allowed}:
                        acceptable_hits += 1
                if opt.word.lower() in {w.lower() for w in case.forbidden_options}:
                    inflation += 1

    return {
        "id": case.id,
        "latency_ms": latency_ms,
        "schema_failed": schema_failed,
        "error": error,
        "flagged": flagged,
        "must_hits": must_hits,
        "must_total": must_total,
        "false_flags": false_flags,
        "acceptable_hits": acceptable_hits,
        "acceptable_total": acceptable_total,
        "inflation": inflation,
        "expect_empty": case.expect_empty,
        "suggestion_count": len(flagged),
    }


async def run_eval(
    session: Session,
    *,
    settings: Settings | None = None,
    model: str | None = None,
    prompt_version: int | None = None,
    gold_path: Path | None = None,
) -> dict[str, Any]:
    """Evaluate the editor role; returns summary plus per-case rows."""
    settings = settings or get_settings()
    if model:
        settings = settings.model_copy(update={"llm_editor_model": model})
    if prompt_version is not None:
        settings = settings.model_copy(update={"llm_editor_prompt_version": prompt_version})

    load_seeds(session)
    cases = load_gold(gold_path)
    rows: list[dict[str, Any]] = []
    for case in cases:
        rows.append(await _run_case(case, session, settings))

    must_hits = sum(r["must_hits"] for r in rows)
    must_total = sum(r["must_total"] for r in rows)
    false_flags = sum(r["false_flags"] for r in rows)
    # Denominator: must_keep checks + empty-case false flags already counted per case.
    keep_checks = sum(len(c.must_keep) for c in cases) + sum(
        r["suggestion_count"] for r in rows if r["expect_empty"]
    )
    acceptable_hits = sum(r["acceptable_hits"] for r in rows)
    acceptable_total = sum(r["acceptable_total"] for r in rows)
    inflation = sum(r["inflation"] for r in rows)
    schema_failures = sum(1 for r in rows if r["schema_failed"])
    latencies = [r["latency_ms"] for r in rows]

    summary = {
        "model": settings.llm_editor_model,
        "prompt_version": settings.llm_editor_prompt_version,
        "cases": len(cases),
        "flag_recall": (must_hits / must_total) if must_total else None,
        "false_flag_rate": (false_flags / keep_checks) if keep_checks else 0.0,
        "option_acceptability": (acceptable_hits / acceptable_total if acceptable_total else None),
        "inflation_count": inflation,
        "schema_failure_rate": schema_failures / len(cases) if cases else 0.0,
        "schema_failures": schema_failures,
        "median_latency_ms": int(statistics.median(latencies)) if latencies else None,
        "generated_at": datetime.now(UTC).isoformat(),
        "cases_detail": rows,
    }
    return summary


def write_results(summary: dict[str, Any]) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    model_slug = str(summary.get("model") or "model").replace("/", "_")
    version = summary.get("prompt_version", 1)
    date = datetime.now(UTC).strftime("%Y%m%d")
    path = RESULTS_DIR / f"{date}-{model_slug}-v{version}.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path
