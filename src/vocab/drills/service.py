"""Generate and grade rewrite drills."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings, get_settings
from vocab.drills.models import Drill, DrillAttempt
from vocab.drills.schemas import DrillGenOutput, DrillGradeOutput
from vocab.drills.select import select_group
from vocab.events import DrillGradedPayload, record_event
from vocab.lexicon.models import PrecisionGroup
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall
from vocab.practice.models import SrsCard
from vocab.practice.srs import review_card


def _group_payload(group: PrecisionGroup) -> dict[str, object]:
    return {
        "id": group.id,
        "head_lemma": group.head_lemma,
        "pos": group.pos,
        "sense_gloss": group.sense_gloss,
        "options": [
            {
                "id": opt.id,
                "word": opt.word,
                "distinction": opt.distinction,
            }
            for opt in group.options
            if opt.status == "approved"
        ],
    }


def _latest_call_id(session: Session, user_id: str, role: str) -> str | None:
    call = session.scalars(
        select(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.role == role)
        .order_by(LlmCall.created_at.desc())
    ).first()
    return call.id if call else None


async def create_drill(
    session: Session,
    *,
    user_id: str,
    settings: Settings | None = None,
) -> Drill:
    """Select a group, generate a vague sentence, persist the drill."""
    settings = settings or get_settings()
    group = select_group(session, user_id)
    result = await run_structured_role(
        "drill_gen",
        {"group": _group_payload(group)},
        user_id=user_id,
        output_model=DrillGenOutput,
        session=session,
        settings=settings,
    )
    assert isinstance(result, DrillGenOutput)
    drill = Drill(
        user_id=user_id,
        group_id=group.id,
        vague_sentence=result.vague_sentence,
        intended_option_id=result.intended_option_id,
        intended_word=result.intended_word,
        llm_call_id=_latest_call_id(session, user_id, "drill_gen"),
    )
    session.add(drill)
    session.commit()
    session.refresh(drill)
    return drill


async def grade_attempt(
    session: Session,
    *,
    drill: Drill,
    user_id: str,
    answer: str,
    settings: Settings | None = None,
) -> DrillAttempt:
    """Grade a rewrite, record events, and maybe review an SRS card."""
    settings = settings or get_settings()
    group = session.scalars(
        select(PrecisionGroup)
        .where(PrecisionGroup.id == drill.group_id)
        .options(selectinload(PrecisionGroup.options))
    ).one()
    result = await run_structured_role(
        "drill_grade",
        {
            "vague_sentence": drill.vague_sentence,
            "answer": answer,
            "group": _group_payload(group),
            "intended_option_id": drill.intended_option_id,
            "intended_word": drill.intended_word,
        },
        user_id=user_id,
        output_model=DrillGradeOutput,
        session=session,
        settings=settings,
    )
    assert isinstance(result, DrillGradeOutput)
    score = result.score
    attempt = DrillAttempt(
        drill_id=drill.id,
        user_id=user_id,
        answer=answer.strip(),
        grade=result.model_dump(),
        score=score,
        llm_call_id=_latest_call_id(session, user_id, "drill_grade"),
    )
    session.add(attempt)
    session.flush()
    record_event(
        session,
        user_id=user_id,
        type="drill_graded",
        subject_type="drill_attempt",
        subject_id=attempt.id,
        payload=DrillGradedPayload(
            score=score,
            rubric={
                "precision": result.precision,
                "meaning": result.meaning,
                "naturalness": result.naturalness,
            },
        ),
    )
    session.commit()
    session.refresh(attempt)

    used_id = result.used_option_id
    if used_id is None:
        # Fallback: detect carded option words in the answer.
        lower = answer.lower()
        for opt in group.options:
            if opt.status == "approved" and opt.word.lower() in lower:
                card = session.scalars(
                    select(SrsCard).where(SrsCard.user_id == user_id, SrsCard.option_id == opt.id)
                ).first()
                if card is not None:
                    used_id = opt.id
                    break
    if used_id and score >= 4:
        card = session.scalars(
            select(SrsCard).where(SrsCard.user_id == user_id, SrsCard.option_id == used_id)
        ).first()
        if card is not None:
            review_card(
                session,
                user_id=user_id,
                option_id=used_id,
                rating="Good",
                source="drill",
            )
    return attempt
