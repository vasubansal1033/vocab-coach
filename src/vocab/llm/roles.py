"""Named LLM roles; application code never hard-codes model strings."""

from __future__ import annotations

from typing import Literal

from vocab.config import Settings

Role = Literal[
    "partner",
    "editor",
    "usage_judge",
    "drill_gen",
    "drill_grade",
    "group_gen",
    "choice_gen",
    "confusable_gen",
    "idiom_gen",
]

ROLES: tuple[Role, ...] = (
    "partner",
    "editor",
    "usage_judge",
    "drill_gen",
    "drill_grade",
    "group_gen",
    "choice_gen",
    "confusable_gen",
    "idiom_gen",
)


def model_for(role: Role, settings: Settings) -> str:
    """Resolve a role to the LiteLLM model string from settings."""
    mapping: dict[Role, str] = {
        "partner": settings.llm_partner_model,
        "editor": settings.llm_editor_model,
        "usage_judge": settings.llm_usage_judge_model,
        "drill_gen": settings.llm_drill_gen_model,
        "drill_grade": settings.llm_drill_grade_model,
        "group_gen": settings.llm_group_gen_model,
        "choice_gen": settings.llm_choice_gen_model,
        "confusable_gen": settings.llm_confusable_gen_model,
        "idiom_gen": settings.llm_idiom_gen_model,
    }
    model = mapping[role]
    if not model or "<" in model:
        raise ValueError(f"LLM_{role.upper()}_MODEL is not configured")
    return model


def prompt_version_for(role: Role, settings: Settings) -> int:
    """Active prompt file version for this role."""
    mapping: dict[Role, int] = {
        "partner": settings.llm_partner_prompt_version,
        "editor": settings.llm_editor_prompt_version,
        "usage_judge": settings.llm_usage_judge_prompt_version,
        "drill_gen": settings.llm_drill_gen_prompt_version,
        "drill_grade": settings.llm_drill_grade_prompt_version,
        "group_gen": settings.llm_group_gen_prompt_version,
        "choice_gen": settings.llm_choice_gen_prompt_version,
        "confusable_gen": settings.llm_confusable_gen_prompt_version,
        "idiom_gen": settings.llm_idiom_gen_prompt_version,
    }
    return mapping[role]
