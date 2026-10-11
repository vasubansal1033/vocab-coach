"""In-process LLM stand-in for unit tests; no network calls."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResponse:
    """Minimal shape matching the LiteLLM fields the client reads."""

    content: str
    input_tokens: int = 1
    output_tokens: int = 1
    cost_usd: float | None = 0.0


@dataclass
class FakeLLM:
    """Return fixture text by role; optional queue for multi-call sequences.

    Install with `vocab.llm.client.use_fake(fake)` in tests.
    """

    # role -> reply string, or a list of successive replies (popped left to right)
    fixtures: Mapping[str, str | Sequence[str]]
    stream_chunks: Mapping[str, Sequence[str]] = field(default_factory=dict)
    calls: list[dict[str, Any]] = field(default_factory=list)
    _queues: dict[str, list[str]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        for role, value in self.fixtures.items():
            if isinstance(value, str):
                self._queues[role] = [value]
            else:
                self._queues[role] = list(value)

    def next_content(self, role: str) -> str:
        """Pop the next fixture for this role."""
        queue = self._queues.get(role)
        if not queue:
            raise KeyError(f"FakeLLM has no remaining fixture for role {role!r}")
        return queue.pop(0)

    async def acompletion(self, *, role: str, **kwargs: object) -> FakeResponse:
        """Record the call and return the next fixture as if from LiteLLM."""
        self.calls.append({"role": role, **kwargs})
        content = self.next_content(role)
        return FakeResponse(content=content)

    async def astream(self, *, role: str, **kwargs: object) -> AsyncIterator[str]:
        """Yield configured chunks for streaming roles."""
        self.calls.append({"role": role, "stream": True, **kwargs})
        chunks = self.stream_chunks.get(role)
        if chunks is None:
            yield self.next_content(role)
            return
        for chunk in chunks:
            yield chunk
