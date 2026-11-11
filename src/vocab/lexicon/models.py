"""Shared precision lexicon and the review queue for new options."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from vocab.db import Base


def new_id() -> str:
    """UUIDv4 string, generated in Python so Postgres needs no special handling."""
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class PrecisionGroup(Base):
    """One word set: precision group, confusable set, or idiom set."""

    __tablename__ = "precision_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # Null for confusable sets; required for precision and idiom.
    head_lemma: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String, default="precision")  # precision|confusable|idiom
    pos: Mapped[str] = mapped_column(String)
    sense_gloss: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)  # draft | approved
    source: Mapped[str] = mapped_column(String)  # seed | llm | review | user
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    options: Mapped[list[PrecisionOption]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class PrecisionOption(Base):
    """One precise alternative for a group."""

    __tablename__ = "precision_options"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("precision_groups.id"), index=True)
    word: Mapped[str] = mapped_column(String)
    distinction: Mapped[str] = mapped_column(Text)
    example: Mapped[str] = mapped_column(Text)
    register: Mapped[str] = mapped_column(String)  # neutral | formal | technical
    status: Mapped[str] = mapped_column(String)  # draft | approved
    # Kind-specific fields; validated by ConfusableDetails / IdiomDetails.
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=None)

    group: Mapped[PrecisionGroup] = relationship(back_populates="options")


class ReviewQueueItem(Base):
    """An editor-proposed word not yet in the lexicon."""

    __tablename__ = "review_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    # Nullable until the Editor section adds editor_runs; no FK yet.
    editor_run_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    head_lemma: Mapped[str] = mapped_column(String, index=True)
    proposed_word: Mapped[str] = mapped_column(String)
    distinction: Mapped[str] = mapped_column(Text)
    example: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LexiconSubmission(Base):
    """Idempotent batch lexicon ingest from a logged-in user."""

    __tablename__ = "lexicon_submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String, index=True)
    request_hash: Mapped[str] = mapped_column(String)
    response: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
