"""Conversations, messages, and per-message lemma counts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vocab.db import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Conversation(Base):
    """One chat thread owned by a user."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    """One user or partner turn in a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user | partner
    content: Mapped[str] = mapped_column(Text)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    lemma_counts: Mapped[list[MessageLemmaCount]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageLemmaCount(Base):
    """Lemma/surface counts for a user message; feeds crutch metrics later."""

    __tablename__ = "message_lemma_counts"
    __table_args__ = (
        UniqueConstraint(
            "message_id",
            "lemma",
            "surface",
            name="uq_lemma_counts_msg_lemma_surface",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    lemma: Mapped[str] = mapped_column(String)
    surface: Mapped[str] = mapped_column(String)
    count: Mapped[int] = mapped_column(Integer)

    message: Mapped[Message] = relationship(back_populates="lemma_counts")
