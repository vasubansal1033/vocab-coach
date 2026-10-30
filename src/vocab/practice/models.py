"""FSRS card state per user and precision option."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from vocab.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class SrsCard(Base):
    """Current FSRS state for one learned option; rebuildable from events."""

    __tablename__ = "srs_cards"
    __table_args__ = (UniqueConstraint("user_id", "option_id", name="uq_srs_cards_user_option"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    option_id: Mapped[str] = mapped_column(ForeignKey("precision_options.id"), index=True)
    fsrs_card: Mapped[dict[str, Any]] = mapped_column(JSON)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
