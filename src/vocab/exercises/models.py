"""Shared exercises and attempts for choice, compare and idiom items."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from vocab.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Exercise(Base):
    """One practice item with a prompt the user sees and a stored answer."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("precision_groups.id"), index=True)
    item_type: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[dict[str, Any]] = mapped_column(JSON)
    answer: Mapped[dict[str, Any]] = mapped_column(JSON)
    llm_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("llm_calls.id"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempts: Mapped[list[ExerciseAttempt]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )


class ExerciseAttempt(Base):
    """One response graded against a stored exercise answer."""

    __tablename__ = "exercise_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    exercise: Mapped[Exercise] = relationship(back_populates="attempts")
