"""Call the usage_judge role for a learned-word hit."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall


class UsageJudgeOutput(BaseModel):
    correct: bool
    explanation: str


async def judge_usage(
    session: Session,
    *,
    user_id: str,
    sentence: str,
    word: str,
    distinction: str,
    settings: Settings | None = None,
) -> tuple[UsageJudgeOutput, str | None]:
    """Return the judge result and the llm_calls id when available."""
    settings = settings or get_settings()
    result = await run_structured_role(
        "usage_judge",
        {
            "sentence": sentence,
            "word": word,
            "distinction": distinction,
        },
        user_id=user_id,
        output_model=UsageJudgeOutput,
        session=session,
        settings=settings,
    )
    assert isinstance(result, UsageJudgeOutput)
    call = session.scalars(
        select(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.role == "usage_judge")
        .order_by(LlmCall.created_at.desc())
    ).first()
    return result, call.id if call else None
