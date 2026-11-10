"""Per-user LLM call and cost ceilings from llm_calls."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.llm.models import LlmCall


def enforce_llm_limits(
    session: Session,
    *,
    user_id: str | None,
    settings: Settings | None = None,
) -> None:
    """Raise 429 when the user is over the rolling 24h call or cost cap."""
    if user_id is None:
        return
    settings = settings or get_settings()
    since = datetime.now(UTC) - timedelta(days=1)
    call_count = session.scalar(
        select(func.count())
        .select_from(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.created_at >= since)
    )
    cost_sum = session.scalar(
        select(func.coalesce(func.sum(LlmCall.cost_usd), 0.0)).where(
            LlmCall.user_id == user_id, LlmCall.created_at >= since
        )
    )
    calls = int(call_count or 0)
    cost = float(cost_sum or 0.0)
    if settings.llm_rate_limit_per_day > 0 and calls >= settings.llm_rate_limit_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily LLM call limit ({settings.llm_rate_limit_per_day}) reached",
        )
    if settings.llm_cost_limit_usd_per_day > 0 and cost >= settings.llm_cost_limit_usd_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily LLM cost limit (${settings.llm_cost_limit_usd_per_day}) reached",
        )
