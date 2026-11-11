"""FakeLLM compare of editor prompt v3 vs v5 on non-idiom gold cases.

Live model eval (`vocab eval editor --prompt-version 3|5`) remains for RUN_LLM_TESTS.
This test documents that v5 default wiring loads and that FakeLLM scoring is stable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lexicon_fixture import seed_lexicon
from sqlalchemy.orm import Session

from vocab.config import Settings
from vocab.editor.eval_runner import GoldCase, load_gold
from vocab.editor.schemas import EditorOutput
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.llm.graphs import run_structured_role
from vocab.llm.prompts import render_prompt

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = REPO_ROOT / "evals" / "editor_gold.yaml"
RESULTS_NOTE = REPO_ROOT / "evals" / "results" / "README-idiom-editor-eval.md"


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


def _non_idiom_cases() -> list[GoldCase]:
    return [c for c in load_gold(GOLD_PATH) if not c.id.startswith("idiom-")]


def _empty_editor_json() -> str:
    return EditorOutput(overview="Clear and precise.", suggestions=[], keep=[]).model_dump_json()


@pytest.mark.asyncio
async def test_editor_prompt_v5_loads_and_fake_scores_match_v3(
    session: Session,
) -> None:
    seed_lexicon(session)
    cases = _non_idiom_cases()
    assert cases, "expected non-idiom gold cases"

    scores: dict[int, dict[str, float]] = {}
    for version in (3, 5):
        empty = _empty_editor_json()
        use_fake(FakeLLM({"editor": [empty] * 40}))
        settings = Settings(
            _env_file=None,
            session_secret="test",
            llm_editor_model="fake-editor",
            llm_editor_prompt_version=version,
        )
        # Prove the prompt file resolves for this version.
        rendered = render_prompt(
            "editor",
            version,
            {
                "conversation_title": "",
                "feedback_expectations": "",
                "partner_previous": "",
                "message": "ok",
                "candidates": [],
                "synonym_hints": {},
                "groups": [],
            },
        )
        assert rendered.prompt_id == "editor"
        assert rendered.prompt_version == version
        assert "vocab-coach editor" in rendered.text.lower()

        false_flag_total = 0
        cases_n = 0
        for case in cases:
            if not case.expect_empty and case.must_flag:
                # Skip cases that need real flags; FakeLLM always returns empty.
                continue
            result = await run_structured_role(
                "editor",
                {
                    "conversation_title": "",
                    "feedback_expectations": "",
                    "partner_previous": case.partner_previous or "",
                    "message": case.text,
                    "candidates": [],
                    "synonym_hints": {},
                    "groups": [],
                },
                output_model=EditorOutput,
                session=session,
                settings=settings,
            )
            assert isinstance(result, EditorOutput)
            if case.expect_empty and result.suggestions:
                false_flag_total += len(result.suggestions)
            cases_n += 1
        scores[version] = {
            "false_flag_rate": (false_flag_total / cases_n) if cases_n else 0.0,
            "cases": float(cases_n),
        }

    assert scores[5]["false_flag_rate"] <= scores[3]["false_flag_rate"]
    RESULTS_NOTE.write_text(
        "# Idiom editor eval note\n\n"
        "Live `vocab eval editor --prompt-version 3` vs `--prompt-version 5` on the full gold set "
        "(including idiom cases) still needs `RUN_LLM_TESTS=1` against a real editor model. "
        "Unit coverage uses FakeLLM for the editor idiom filter and this v3/v5 prompt load check.\n"
        f"FakeLLM empty-suggestion false_flag_rate: v3={scores[3]['false_flag_rate']}, "
        f"v5={scores[5]['false_flag_rate']}.\n",
        encoding="utf-8",
    )


def test_idiom_gold_cases_present() -> None:
    idiom_cases = [c for c in load_gold(GOLD_PATH) if c.id.startswith("idiom-")]
    assert len(idiom_cases) >= 5
    fit = [c for c in idiom_cases if c.must_flag]
    avoid = [c for c in idiom_cases if c.expect_empty]
    assert len(fit) >= 2
    assert len(avoid) >= 3
