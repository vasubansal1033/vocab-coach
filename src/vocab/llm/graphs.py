"""LangGraph workflows that orchestrate role-based LLM calls.

LiteLLM stays inside `client.py`. Graphs decide which roles run and in what
order; nodes call `complete` / `stream` so FakeLLM, limits, and llm_calls logging
keep working unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.llm.client import complete, stream
from vocab.llm.roles import Role


class StructuredState(TypedDict, total=False):
    """Shared state for a single structured role call."""

    role: Role
    variables: dict[str, Any]
    result: BaseModel | str


class PartnerState(TypedDict, total=False):
    variables: dict[str, Any]
    history: list[dict[str, str]]
    text: str


class JudgeHit(TypedDict):
    word: str
    distinction: str


class JudgeState(TypedDict, total=False):
    sentence: str
    hits: list[JudgeHit]
    judgments: list[dict[str, Any]]


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    return dict(config.get("configurable") or {})


async def _structured_node(state: StructuredState, config: RunnableConfig) -> StructuredState:
    conf = _cfg(config)
    role: Role = state["role"]
    result = await complete(
        role,
        state["variables"],
        user_id=conf.get("user_id"),
        output_model=conf.get("output_model"),
        session=conf.get("session"),
        settings=conf.get("settings"),
        prompts_dir=conf.get("prompts_dir"),
    )
    return {"result": result}


def _build_structured_graph():  # noqa: ANN202
    graph = StateGraph(StructuredState)
    graph.add_node("call_role", _structured_node)
    graph.add_edge(START, "call_role")
    graph.add_edge("call_role", END)
    return graph.compile()


_structured_graph = _build_structured_graph()


async def run_structured_role[T: BaseModel](
    role: Role,
    variables: dict[str, Any],
    *,
    user_id: str | None = None,
    output_model: type[T] | None = None,
    session: Session | None = None,
    settings: Settings | None = None,
    prompts_dir: Path | None = None,
) -> str | T:
    """Run one structured (or plain) role through the LangGraph role node."""
    settings = settings or get_settings()
    final = await _structured_graph.ainvoke(
        {"role": role, "variables": variables},
        config={
            "configurable": {
                "user_id": user_id,
                "output_model": output_model,
                "session": session,
                "settings": settings,
                "prompts_dir": prompts_dir,
            }
        },
    )
    return final["result"]


async def _partner_node(state: PartnerState, config: RunnableConfig) -> PartnerState:
    conf = _cfg(config)
    writer = get_stream_writer()
    chunks: list[str] = []
    async for chunk in stream(
        "partner",
        state["variables"],
        user_id=conf.get("user_id"),
        session=conf.get("session"),
        settings=conf.get("settings"),
        prompts_dir=conf.get("prompts_dir"),
        history=state.get("history"),
    ):
        writer(chunk)
        chunks.append(chunk)
    return {"text": "".join(chunks)}


def _build_partner_graph():  # noqa: ANN202
    graph = StateGraph(PartnerState)
    graph.add_node("partner", _partner_node)
    graph.add_edge(START, "partner")
    graph.add_edge("partner", END)
    return graph.compile()


_partner_graph = _build_partner_graph()


async def run_partner_stream(
    variables: dict[str, Any],
    *,
    user_id: str | None = None,
    session: Session | None = None,
    settings: Settings | None = None,
    prompts_dir: Path | None = None,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[str]:
    """Stream partner tokens via LangGraph custom stream mode."""
    settings = settings or get_settings()
    async for item in _partner_graph.astream(
        {"variables": variables, "history": history or []},
        config={
            "configurable": {
                "user_id": user_id,
                "session": session,
                "settings": settings,
                "prompts_dir": prompts_dir,
            }
        },
        stream_mode="custom",
    ):
        yield str(item)


async def _judge_all_node(state: JudgeState, config: RunnableConfig) -> JudgeState:
    """Judge each learned-word hit in order inside one graph step."""
    conf = _cfg(config)
    from vocab.practice.judge import UsageJudgeOutput

    judgments: list[dict[str, Any]] = []
    for hit in state.get("hits") or []:
        result = await complete(
            "usage_judge",
            {
                "sentence": state["sentence"],
                "word": hit["word"],
                "distinction": hit["distinction"],
            },
            user_id=conf.get("user_id"),
            output_model=UsageJudgeOutput,
            session=conf.get("session"),
            settings=conf.get("settings"),
        )
        assert isinstance(result, UsageJudgeOutput)
        judgments.append(
            {
                "word": hit["word"],
                "correct": result.correct,
                "explanation": result.explanation,
            }
        )
    return {"judgments": judgments}


def _build_judge_graph():  # noqa: ANN202
    graph = StateGraph(JudgeState)
    graph.add_node("judge_hits", _judge_all_node)
    graph.add_edge(START, "judge_hits")
    graph.add_edge("judge_hits", END)
    return graph.compile()


_judge_graph = _build_judge_graph()


async def run_usage_judges(
    *,
    sentence: str,
    hits: list[JudgeHit],
    user_id: str,
    session: Session,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Run the multi-hit usage-judge graph; returns one judgment dict per hit."""
    settings = settings or get_settings()
    if not hits:
        return []
    final = await _judge_graph.ainvoke(
        {"sentence": sentence, "hits": hits},
        config={
            "configurable": {
                "user_id": user_id,
                "session": session,
                "settings": settings,
            }
        },
    )
    return list(final.get("judgments") or [])
