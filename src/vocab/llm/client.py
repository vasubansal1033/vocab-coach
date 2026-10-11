"""Call models by role: prompts, structured output, retries, and logging."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session, sessionmaker

from vocab.config import Settings, get_settings
from vocab.db import get_engine
from vocab.llm.fake import FakeLLM
from vocab.llm.limits import enforce_llm_limits
from vocab.llm.models import LlmCall
from vocab.llm.prompts import render_prompt
from vocab.llm.roles import Role, model_for, prompt_version_for

_fake: FakeLLM | None = None


def use_fake(fake: FakeLLM | None) -> None:
    """Install or clear a FakeLLM for tests."""
    global _fake
    _fake = fake


def _session_scope(session: Session | None) -> tuple[Session, bool]:
    """Use the caller's session, or open a short-lived one for the row insert."""
    if session is not None:
        return session, False
    maker = sessionmaker(get_engine(), expire_on_commit=False)
    return maker(), True


def _record(
    session: Session,
    *,
    user_id: str | None,
    role: str,
    model: str,
    prompt_id: str,
    prompt_version: int,
    input_tokens: int | None,
    output_tokens: int | None,
    cost_usd: float | None,
    latency_ms: int,
    status: str,
    error: str | None,
) -> LlmCall:
    row = LlmCall(
        user_id=user_id,
        role=role,
        model=model,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        status=status,
        error=error,
    )
    session.add(row)
    session.commit()
    return row


def _ollama_kwargs(model: str, settings: Settings) -> dict[str, Any]:
    if model.startswith("ollama"):
        return {"api_base": settings.ollama_api_base}
    return {}


def _supports_schema(model: str) -> bool:
    import litellm

    return bool(litellm.supports_response_schema(model=model))


def _extract_content(response: object) -> str:
    if hasattr(response, "choices"):
        return str(response.choices[0].message.content or "")  # type: ignore[attr-defined]
    return str(getattr(response, "content", response))


def _usage_and_cost(response: object) -> tuple[int | None, int | None, float | None]:
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    output_tokens = getattr(usage, "completion_tokens", None) if usage else None
    hidden = getattr(response, "_hidden_params", None) or {}
    cost = hidden.get("response_cost") if isinstance(hidden, dict) else None
    if cost is None and hasattr(response, "cost_usd"):
        cost = response.cost_usd  # type: ignore[attr-defined]
    if input_tokens is None and hasattr(response, "input_tokens"):
        input_tokens = response.input_tokens  # type: ignore[attr-defined]
    if output_tokens is None and hasattr(response, "output_tokens"):
        output_tokens = response.output_tokens  # type: ignore[attr-defined]
    return input_tokens, output_tokens, cost


async def _acompletion(
    *,
    role: Role,
    model: str,
    messages: list[dict[str, str]],
    **kwargs: object,
) -> object:
    if _fake is not None:
        return await _fake.acompletion(role=role, model=model, messages=messages, **kwargs)
    import litellm

    return await litellm.acompletion(model=model, messages=messages, **kwargs)


async def complete[T: BaseModel](
    role: Role,
    variables: dict[str, Any],
    *,
    user_id: str | None = None,
    output_model: type[T] | None = None,
    session: Session | None = None,
    settings: Settings | None = None,
    prompts_dir: Path | None = None,
) -> str | T:
    """Run a non-streaming role call; validate and retry once on bad JSON."""
    settings = settings or get_settings()
    model = model_for(role, settings)
    version = prompt_version_for(role, settings)
    rendered = render_prompt(role, version, variables, prompts_dir=prompts_dir)
    messages: list[dict[str, str]] = [{"role": "system", "content": rendered.text}]

    call_kwargs: dict[str, Any] = {**_ollama_kwargs(model, settings)}
    if output_model is not None:
        if _supports_schema(model):
            call_kwargs["response_format"] = output_model
        else:
            call_kwargs["response_format"] = {"type": "json_object"}
            messages[0] = {
                "role": "system",
                "content": (
                    f"{rendered.text}\n\n"
                    "Respond with a JSON object matching this schema:\n"
                    f"{json.dumps(output_model.model_json_schema())}"
                ),
            }

    db, owns = _session_scope(session)
    enforce_llm_limits(db, user_id=user_id, settings=settings)
    started = time.perf_counter()
    try:
        response = await _acompletion(role=role, model=model, messages=messages, **call_kwargs)
        content = _extract_content(response)
        input_tokens, output_tokens, cost = _usage_and_cost(response)

        if output_model is None:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _record(
                db,
                user_id=user_id,
                role=role,
                model=model,
                prompt_id=rendered.prompt_id,
                prompt_version=rendered.prompt_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                status="ok",
                error=None,
            )
            return content

        try:
            parsed: T = output_model.model_validate_json(content)
        except ValidationError as first_error:
            # One retry with the validation error in the conversation.
            retry_messages = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "Your previous reply failed validation:\n"
                        f"{first_error}\n"
                        "Reply again with valid JSON only."
                    ),
                },
            ]
            response = await _acompletion(
                role=role, model=model, messages=retry_messages, **call_kwargs
            )
            content = _extract_content(response)
            input_tokens, output_tokens, cost = _usage_and_cost(response)
            try:
                parsed = output_model.model_validate_json(content)
            except ValidationError as second_error:
                latency_ms = int((time.perf_counter() - started) * 1000)
                _record(
                    db,
                    user_id=user_id,
                    role=role,
                    model=model,
                    prompt_id=rendered.prompt_id,
                    prompt_version=rendered.prompt_version,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost,
                    latency_ms=latency_ms,
                    status="error",
                    error=str(second_error),
                )
                raise

        latency_ms = int((time.perf_counter() - started) * 1000)
        _record(
            db,
            user_id=user_id,
            role=role,
            model=model,
            prompt_id=rendered.prompt_id,
            prompt_version=rendered.prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status="ok",
            error=None,
        )
        return parsed
    except ValidationError:
        raise
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record(
            db,
            user_id=user_id,
            role=role,
            model=model,
            prompt_id=rendered.prompt_id,
            prompt_version=rendered.prompt_version,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            latency_ms=latency_ms,
            status="error",
            error=str(exc),
        )
        raise
    finally:
        if owns:
            db.close()


async def stream(
    role: Role,
    variables: dict[str, Any],
    *,
    user_id: str | None = None,
    session: Session | None = None,
    settings: Settings | None = None,
    prompts_dir: Path | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    """Stream text chunks for the partner role."""
    settings = settings or get_settings()
    model = model_for(role, settings)
    version = prompt_version_for(role, settings)
    rendered = render_prompt(role, version, variables, prompts_dir=prompts_dir)
    messages: list[dict[str, str]] = [{"role": "system", "content": rendered.text}]
    if history:
        messages.extend(history)
    call_kwargs = {**_ollama_kwargs(model, settings)}

    db, owns = _session_scope(session)
    enforce_llm_limits(db, user_id=user_id, settings=settings)
    started = time.perf_counter()
    error: str | None = None
    status = "ok"
    try:
        if _fake is not None:
            async for chunk in _fake.astream(
                role=role, model=model, messages=messages, **call_kwargs
            ):
                yield chunk
        else:
            import litellm

            response = await litellm.acompletion(
                model=model,
                messages=messages,
                stream=True,
                **call_kwargs,
            )
            async for part in response:
                delta = part.choices[0].delta
                text = getattr(delta, "content", None) or ""
                if text:
                    yield text
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record(
            db,
            user_id=user_id,
            role=role,
            model=model,
            prompt_id=rendered.prompt_id,
            prompt_version=rendered.prompt_version,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            latency_ms=latency_ms,
            status=status,
            error=error,
        )
        if owns:
            db.close()


async def ping(
    role: Role,
    *,
    session: Session | None = None,
    settings: Settings | None = None,
) -> tuple[str, int]:
    """Tiny probe against the configured model; used by `vocab llm ping`."""
    settings = settings or get_settings()
    model = model_for(role, settings)
    messages = [
        {
            "role": "user",
            "content": "Reply with the single word pong and nothing else.",
        }
    ]
    call_kwargs = {**_ollama_kwargs(model, settings)}
    db, owns = _session_scope(session)
    started = time.perf_counter()
    try:
        response = await _acompletion(role=role, model=model, messages=messages, **call_kwargs)
        content = _extract_content(response)
        input_tokens, output_tokens, cost = _usage_and_cost(response)
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record(
            db,
            user_id=None,
            role=role,
            model=model,
            prompt_id="ping",
            prompt_version=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            status="ok",
            error=None,
        )
        return content, latency_ms
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record(
            db,
            user_id=None,
            role=role,
            model=model,
            prompt_id="ping",
            prompt_version=1,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            latency_ms=latency_ms,
            status="error",
            error=str(exc),
        )
        raise
    finally:
        if owns:
            db.close()
