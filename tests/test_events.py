"""record_event validates payloads."""

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.events import Event, SuggestionShownPayload, record_event


def test_record_event_round_trip(session: Session, make_user) -> None:
    user = make_user()
    record_event(
        session,
        user_id=user.id,
        type="suggestion_shown",
        subject_type="suggestion",
        subject_id="s1",
        payload=SuggestionShownPayload(group_id="fix.repair"),
    )
    session.commit()
    row = session.scalars(select(Event)).one()
    assert row.payload == {"group_id": "fix.repair"}


def test_record_event_rejects_bad_payload(session: Session, make_user) -> None:
    user = make_user()
    with pytest.raises(ValidationError):
        record_event(
            session,
            user_id=user.id,
            type="suggestion_accepted",
            subject_type="suggestion",
            subject_id="s1",
            payload={"option_id": None},  # missing word
        )
