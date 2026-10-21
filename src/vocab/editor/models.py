"""Persisted editor runs and anchored suggestions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from vocab.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class EditorRun(Base):
    """Validated editor output for one user message."""

    __tablename__ = "editor_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    # No FK to messages yet; Conversation UI adds that table.
    message_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    llm_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("llm_calls.id"), nullable=True, default=None
    )
    output: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    suggestions: Mapped[list[Suggestion]] = relationship(
        back_populates="editor_run", cascade="all, delete-orphan"
    )


class Suggestion(Base):
    """One anchored rewrite suggestion shown to the user."""

    __tablename__ = "suggestions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    editor_run_id: Mapped[str] = mapped_column(ForeignKey("editor_runs.id"), index=True)
    message_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    original_text: Mapped[str] = mapped_column(String)
    span_start: Mapped[int] = mapped_column(Integer)
    span_end: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[str | None] = mapped_column(
        ForeignKey("precision_groups.id"), nullable=True, default=None
    )
    question: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    rank: Mapped[int] = mapped_column(Integer)

    editor_run: Mapped[EditorRun] = relationship(back_populates="suggestions")
    options: Mapped[list[SuggestionOption]] = relationship(
        back_populates="suggestion", cascade="all, delete-orphan"
    )


class SuggestionOption(Base):
    """One word choice under a suggestion."""

    __tablename__ = "suggestion_options"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    suggestion_id: Mapped[str] = mapped_column(ForeignKey("suggestions.id"), index=True)
    option_id: Mapped[str | None] = mapped_column(
        ForeignKey("precision_options.id"), nullable=True, default=None
    )
    word: Mapped[str] = mapped_column(String)
    meaning: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(Integer)

    suggestion: Mapped[Suggestion] = relationship(back_populates="options")
