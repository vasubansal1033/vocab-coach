"""Persisted record of every LLM call, including failures."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from vocab.db import Base


def new_id() -> str:
    """UUIDv4 string, generated in Python so Postgres needs no special handling."""
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class LlmCall(Base):
    """One model invocation; metrics and cost trace back here."""

    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True, default=None
    )
    role: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    prompt_id: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[int] = mapped_column(Integer)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    latency_ms: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
