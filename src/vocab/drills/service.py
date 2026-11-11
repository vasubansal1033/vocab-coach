"""Generate and grade rewrite drills."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings, get_settings
from vocab.drills.models import Drill, DrillAttempt
from vocab.drills.schemas import DrillGenOutput, DrillGenOutputV2, DrillGradeOutput
from vocab.drills.select import select_group
from vocab.events import DrillDisputedPayload, DrillGradedPayload, Event, record_event
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
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


def _load_group(session: Session, group_id: str) -> PrecisionGroup:
    return session.scalars(
        select(PrecisionGroup)
        .where(PrecisionGroup.id == group_id)
        .options(selectinload(PrecisionGroup.options))
    ).one()


def _intended_option(group: PrecisionGroup, option_id: str) -> PrecisionOption | None:
    for opt in group.options:
        if opt.id == option_id:
            return opt
    return None


def gen_output_model(prompt_version: int) -> type[DrillGenOutput]:
    """Pick the structured output model that matches the active drill_gen prompt."""
    if prompt_version >= 2:
        return DrillGenOutputV2
    return DrillGenOutput


async def create_drill(
    session: Session,
    *,
    user_id: str,
    settings: Settings | None = None,
) -> Drill:
    """Select a group, generate a vague sentence, persist the drill."""
    settings = settings or get_settings()
    group = select_group(session, user_id)
    output_model = gen_output_model(settings.llm_drill_gen_prompt_version)
    result = await run_structured_role(
        "drill_gen",
        {"group": _group_payload(group)},
        user_id=user_id,
        output_model=output_model,
        session=session,
        settings=settings,
    )
    assert isinstance(result, DrillGenOutput)
    context = result.context if isinstance(result, DrillGenOutputV2) else None
    drill = Drill(
        user_id=user_id,
        group_id=group.id,
        vague_sentence=result.vague_sentence,
        context=context,
        intended_option_id=result.intended_option_id,
        intended_word=result.intended_word,
        llm_call_id=_latest_call_id(session, user_id, "drill_gen"),
    )
    session.add(drill)
    session.commit()
    session.refresh(drill)
    return drill


def hint_for(session: Session, drill: Drill, level: int) -> str:
    """Return a progressive hint; levels do not call an LLM."""
    if level not in (1, 2, 3):
        raise ValueError("hint level must be 1, 2 or 3")
    group = _load_group(session, drill.group_id)
    intended = _intended_option(group, drill.intended_option_id)
    if level == 1:
        if intended is None or not intended.distinction.strip():
            return "Think about what makes this situation distinct."
        return intended.distinction.strip()
    if level == 2:
        word = (drill.intended_word or "").strip()
        if not word:
            return "The intended word starts with an unknown letter."
        return f"The intended word starts with “{word[0]}”."
    words = sorted(
        {opt.word for opt in group.options if opt.status == "approved" and opt.word.strip()}
    )
    if not words:
        return "No approved options are available for this group."
    return "Options in this group: " + ", ".join(words) + "."


@dataclass(frozen=True)
class DrillSummary:
    mean_score: float
    words_practised: list[str]
    total_hints_used: int


def summarize_attempts(attempts: Sequence[DrillAttempt]) -> DrillSummary:
    """Aggregate scores and hints from stored attempts; no DB writes."""
    if not attempts:
        return DrillSummary(mean_score=0.0, words_practised=[], total_hints_used=0)
    mean = sum(a.score for a in attempts) / len(attempts)
    words: list[str] = []
    seen: set[str] = set()
    for attempt in attempts:
        word = attempt.drill.intended_word if attempt.drill is not None else ""
        if word and word not in seen:
            seen.add(word)
            words.append(word)
    return DrillSummary(
        mean_score=round(mean, 2),
        words_practised=words,
        total_hints_used=sum(a.hints_used for a in attempts),
    )


def dispute_attempt(
    session: Session,
    *,
    attempt: DrillAttempt,
    user_id: str,
    note: str | None = None,
) -> Event:
    """Record a dispute; never writes eval files from a web request."""
    cleaned = note.strip() if note and note.strip() else None
    event = record_event(
        session,
        user_id=user_id,
        type="drill_disputed",
        subject_type="drill_attempt",
        subject_id=attempt.id,
        payload=DrillDisputedPayload(note=cleaned),
    )
    session.commit()
    session.refresh(event)
    return event


def intended_distinction(session: Session, drill: Drill) -> str | None:
    """Look up the intended option's distinction for the grade view."""
    group = _load_group(session, drill.group_id)
    intended = _intended_option(group, drill.intended_option_id)
    if intended is None:
        return None
    text = intended.distinction.strip()
    return text or None


async def grade_attempt(
    session: Session,
    *,
    drill: Drill,
    user_id: str,
    answer: str,
    hints_used: int = 0,
    settings: Settings | None = None,
) -> DrillAttempt:
    """Grade a rewrite, record events, and maybe review an SRS card."""
    settings = settings or get_settings()
    group = _load_group(session, drill.group_id)
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
        hints_used=max(0, min(3, hints_used)),
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


def _disputes_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "evals" / "drill_disputes"


def last_export_date(disputes_dir: Path | None = None) -> date | None:
    """Newest YYYY-MM-DD stem in the disputes folder, if any."""
    folder = disputes_dir or _disputes_dir()
    if not folder.is_dir():
        return None
    dates: list[date] = []
    for path in folder.glob("*.yaml"):
        try:
            dates.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    return max(dates) if dates else None


def export_drill_disputes(
    session: Session,
    *,
    disputes_dir: Path | None = None,
    as_of: date | None = None,
) -> Path:
    """Write disputes since the last export file into evals/drill_disputes/<date>.yaml."""
    folder = disputes_dir or _disputes_dir()
    folder.mkdir(parents=True, exist_ok=True)
    since = last_export_date(folder)
    export_day = as_of or date.today()
    query = (
        select(Event)
        .where(Event.type == "drill_disputed")
        .order_by(Event.created_at.asc())
    )
    events = list(session.scalars(query))
    rows: list[dict[str, object]] = []
    for event in events:
        if since is not None and event.created_at.date() <= since:
            continue
        attempt = session.get(DrillAttempt, event.subject_id)
        if attempt is None:
            continue
        drill = session.get(Drill, attempt.drill_id)
        if drill is None:
            continue
        payload = event.payload if isinstance(event.payload, dict) else {}
        rows.append(
            {
                "event_id": event.id,
                "attempt_id": attempt.id,
                "user_id": event.user_id,
                "created_at": event.created_at.isoformat(),
                "vague_sentence": drill.vague_sentence,
                "context": drill.context,
                "intended_word": drill.intended_word,
                "answer": attempt.answer,
                "grade": attempt.grade,
                "score": attempt.score,
                "hints_used": attempt.hints_used,
                "note": payload.get("note"),
            }
        )
    out_path = folder / f"{export_day.isoformat()}.yaml"
    payload = {
        "exported_on": export_day.isoformat(),
        "since": since.isoformat() if since else None,
        "disputes": rows,
    }
    out_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return out_path
