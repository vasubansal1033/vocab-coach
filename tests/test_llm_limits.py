"""Per-user LLM rate and cost ceilings."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.config import Settings
from vocab.llm.limits import enforce_llm_limits
from vocab.llm.models import LlmCall


def test_rate_limit_blocks(
    session: Session, make_user: Callable[..., User]
) -> None:
    user = make_user()
    for i in range(3):
        session.add(
            LlmCall(
                id=f"call-{i}",
                user_id=user.id,
                role="editor",
                model="m",
                prompt_id="editor",
                prompt_version=1,
                input_tokens=1,
                output_tokens=1,
                cost_usd=0.01,
                latency_ms=1,
                status="ok",
                error=None,
                created_at=datetime.now(UTC),
            )
        )
    session.commit()
    settings = Settings(
        _env_file=None,
        session_secret="test",
        llm_rate_limit_per_day=3,
        llm_cost_limit_usd_per_day=10.0,
    )
    with pytest.raises(HTTPException) as exc:
        enforce_llm_limits(session, user_id=user.id, settings=settings)
    assert exc.value.status_code == 429


def test_cost_limit_blocks(
    session: Session, make_user: Callable[..., User]
) -> None:
    user = make_user()
    session.add(
        LlmCall(
            id="call-cost",
            user_id=user.id,
            role="editor",
            model="m",
            prompt_id="editor",
            prompt_version=1,
            input_tokens=1,
            output_tokens=1,
            cost_usd=2.5,
            latency_ms=1,
            status="ok",
            error=None,
            created_at=datetime.now(UTC),
        )
    )
    session.commit()
    settings = Settings(
        _env_file=None,
        session_secret="test",
        llm_rate_limit_per_day=100,
        llm_cost_limit_usd_per_day=2.0,
    )
    with pytest.raises(HTTPException) as exc:
        enforce_llm_limits(session, user_id=user.id, settings=settings)
    assert exc.value.status_code == 429
