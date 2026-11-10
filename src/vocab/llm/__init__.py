"""LLM access by role; the only package that imports litellm or LangGraph."""

from vocab.llm.client import complete, ping, stream
from vocab.llm.fake import FakeLLM
from vocab.llm.graphs import run_partner_stream, run_structured_role, run_usage_judges

__all__ = [
    "FakeLLM",
    "complete",
    "ping",
    "run_partner_stream",
    "run_structured_role",
    "run_usage_judges",
    "stream",
]
