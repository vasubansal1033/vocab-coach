"""Rewrite drills and graded attempts."""

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


class Drill(Base):
    """One vague sentence targeting a precision group."""

    __tablename__ = "drills"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("precision_groups.id"), index=True)
    vague_sentence: Mapped[str] = mapped_column(Text)
    intended_option_id: Mapped[str] = mapped_column(String, default="")
    intended_word: Mapped[str] = mapped_column(String, default="")
    llm_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("llm_calls.id"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    attempts: Mapped[list[DrillAttempt]] = relationship(
        back_populates="drill", cascade="all, delete-orphan"
    )


class DrillAttempt(Base):
    """One rewrite and its grade for a drill."""

    __tablename__ = "drill_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    drill_id: Mapped[str] = mapped_column(ForeignKey("drills.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    answer: Mapped[str] = mapped_column(Text)
    grade: Mapped[dict[str, Any]] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    llm_call_id: Mapped[str | None] = mapped_column(
        ForeignKey("llm_calls.id"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    drill: Mapped[Drill] = relationship(back_populates="attempts")
