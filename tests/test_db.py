import pytest
from sqlalchemy import ForeignKey, String, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column

from vocab.db import make_engine


def test_pragmas_are_on(engine) -> None:
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_foreign_key_violation_raises() -> None:
    """Proves the pragma is on: SQLite would silently accept the orphan otherwise."""
    Local = declarative_base()

    class Parent(Local):
        __tablename__ = "parent"
        id: Mapped[str] = mapped_column(String, primary_key=True)

    class Child(Local):
        __tablename__ = "child"
        id: Mapped[str] = mapped_column(String, primary_key=True)
        parent_id: Mapped[str] = mapped_column(ForeignKey("parent.id"))

    engine = make_engine("sqlite://")
    Local.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Child(id="c1", parent_id="missing"))
        with pytest.raises(IntegrityError):
            session.commit()
