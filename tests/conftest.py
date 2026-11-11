import os
from collections.abc import Callable, Iterator

# vocab.main builds `app` at import time and refuses an empty secret.
os.environ.setdefault("SESSION_SECRET", "test-session-secret")

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from vocab import events as _events  # noqa: F401  registers tables
from vocab.auth import models as _auth_models  # noqa: F401  registers tables
from vocab.auth.deps import SESSION_KEY, current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.conversation import models as _conversation_models  # noqa: F401  registers tables
from vocab.db import Base, get_session, make_engine
from vocab.drills import models as _drills_models  # noqa: F401  registers tables
from vocab.editor import models as _editor_models  # noqa: F401  registers tables
from vocab.exercises import models as _exercises_models  # noqa: F401  registers tables
from vocab.lexicon import models as _lexicon_models  # noqa: F401  registers tables
from vocab.llm import models as _llm_models  # noqa: F401  registers tables
from vocab.main import create_app
from vocab.practice import models as _practice_models  # noqa: F401  registers tables


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip @pytest.mark.llm unless RUN_LLM_TESTS=1."""
    if os.environ.get("RUN_LLM_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="set RUN_LLM_TESTS=1 to call real models")
    for item in items:
        if item.get_closest_marker("llm") is not None:
            item.add_marker(skip)


@pytest.fixture
def engine() -> Engine:
    """In-memory SQLite with the same pragmas as production."""
    engine = make_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session


@pytest.fixture
def app(session: Session) -> FastAPI:
    """A fresh app wired to the test database."""
    app = create_app(Settings(_env_file=None, session_secret="test-session-secret"))
    app.dependency_overrides[get_session] = lambda: session

    @app.get("/_test/session/{user_id}")
    def _set_session(user_id: str, request: Request) -> dict[str, str]:
        """Plant a real session cookie, so `current_user` itself is exercised."""
        request.session[SESSION_KEY] = user_id
        return {"ok": "1"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Anonymous client: no session cookie."""
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def make_user(session: Session) -> Callable[..., User]:
    def _make(display_name: str = "Test User") -> User:
        user = User(display_name=display_name)
        session.add(user)
        session.commit()
        return user

    return _make


@pytest.fixture
def login_as(app: FastAPI) -> Callable[[User], None]:
    """Log a fake user in through `dependency_overrides`, for tests that skip the cookie."""

    def _login(user: User) -> None:
        app.dependency_overrides[current_user] = lambda: user

    return _login
