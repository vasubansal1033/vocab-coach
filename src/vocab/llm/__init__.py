"""LLM access by role; the only package that imports litellm."""

from vocab.llm.client import complete, ping, stream
from vocab.llm.fake import FakeLLM

__all__ = ["FakeLLM", "complete", "ping", "stream"]
