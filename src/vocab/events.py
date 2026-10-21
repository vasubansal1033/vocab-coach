"""Append-only behavioural events; metrics read these, never live counters."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.types import JSON

from vocab.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Event(Base):
    """One recorded behaviour; filter every query by user_id."""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String, index=True)
    subject_type: Mapped[str] = mapped_column(String)
    subject_id: Mapped[str] = mapped_column(String)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SuggestionShownPayload(BaseModel):
    group_id: str | None = None


class SuggestionAcceptedPayload(BaseModel):
    option_id: str | None = None
    word: str


class SuggestionDismissedPayload(BaseModel):
    """No fields; presence of the event is the signal."""


class WordUsedPayload(BaseModel):
    option_id: str
    correct: bool
    prompted: bool
    judge_call_id: str | None = None


class CardReviewedPayload(BaseModel):
    rating: str
    source: Literal["conversation", "drill", "review_page"]
    # Stored so `vocab srs rebuild` can replay without the old card row.
    option_id: str


class DrillGradedPayload(BaseModel):
    score: int
    rubric: dict[str, Any] = Field(default_factory=dict)


PAYLOAD_MODELS: dict[str, type[BaseModel]] = {
    "suggestion_shown": SuggestionShownPayload,
    "suggestion_accepted": SuggestionAcceptedPayload,
    "suggestion_dismissed": SuggestionDismissedPayload,
    "word_used": WordUsedPayload,
    "card_reviewed": CardReviewedPayload,
    "drill_graded": DrillGradedPayload,
}


def record_event(
    session: Session,
    *,
    user_id: str,
    type: str,
    subject_type: str,
    subject_id: str,
    payload: BaseModel | dict[str, Any] | None = None,
) -> Event:
    """Validate and append one event; callers commit with their unit of work."""
    model = PAYLOAD_MODELS.get(type)
    if model is None:
        raise ValueError(f"unknown event type: {type}")
    if payload is None:
        data = model().model_dump()
    elif isinstance(payload, BaseModel):
        data = model.model_validate(payload.model_dump()).model_dump()
    else:
        data = model.model_validate(payload).model_dump()
    row = Event(
        user_id=user_id,
        type=type,
        subject_type=subject_type,
        subject_id=subject_id,
        payload=data,
    )
    session.add(row)
    return row
