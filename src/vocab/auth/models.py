"""Internal users and the OIDC identities that map onto them."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from vocab.db import Base


def new_id() -> str:
    """UUIDv4 string, generated in Python so Postgres needs no special handling."""
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """The internal user; every other table points here, never at an OIDC subject."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Identity(Base):
    """Maps `(issuer, subject)` to a user so a provider change never changes `users.id`."""

    __tablename__ = "identities"
    __table_args__ = (UniqueConstraint("issuer", "subject", name="uq_identities_issuer_subject"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    issuer: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
