"""Run the editor on a user message and persist anchored suggestions."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from vocab.config import Settings, get_settings
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.editor.schemas import EditorOutput, EditorSuggestion
from vocab.events import SuggestionShownPayload, record_event
from vocab.lexicon.models import PrecisionGroup, PrecisionOption, ReviewQueueItem
from vocab.lexicon.service import approved_groups_for_lemma
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall
from vocab.nlp.analyzer import analyze

logger = logging.getLogger(__name__)


def _find_span(message: str, original: str) -> tuple[int, int] | None:
    """Locate exact substring; models must not invent character offsets."""
    start = message.find(original)
    if start < 0:
        return None
    return start, start + len(original)


def _groups_payload(groups: list[PrecisionGroup]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for group in groups:
        out.append(
            {
                "id": group.id,
                "head_lemma": group.head_lemma,
                "pos": group.pos,
                "sense_gloss": group.sense_gloss,
                "options": [
                    {
                        "id": opt.id,
                        "word": opt.word,
                        "distinction": opt.distinction,
                        "example": opt.example,
                    }
                    for opt in group.options
                    if opt.status == "approved"
                ],
            }
        )
    return out


def _resolve_option_id(
    session: Session,
    word: str,
    option_id: str | None,
    group_id: str | None,
) -> str | None:
    """Trust option_id only when it exists; otherwise try group+word."""
    if option_id:
        row = session.get(PrecisionOption, option_id)
        if row is not None:
            return row.id
    if group_id:
        oid = f"{group_id}/{word}"
        if session.get(PrecisionOption, oid) is not None:
            return oid
    return None


async def analyze_message(
    session: Session,
    *,
    user_id: str,
    message_id: str,
    message: str,
    partner_previous: str | None = None,
    conversation_title: str | None = None,
    feedback_expectations: str | None = None,
    settings: Settings | None = None,
    record_shown: bool = True,
) -> list[Suggestion]:
    """Analyze text, call the editor role, anchor spans, persist suggestions."""
    settings = settings or get_settings()
    analysis = analyze(message)

    lemma_set = {span.lemma for span in analysis.candidates}
    groups: list[PrecisionGroup] = []
    for lemma in sorted(lemma_set):
        groups.extend(approved_groups_for_lemma(session, lemma))

    # Also try surface-form lemmas from crutch hits (fix from fixed).
    variables = {
        "message": message,
        "partner_previous": partner_previous or "",
        "conversation_title": conversation_title or "",
        "feedback_expectations": (feedback_expectations or "").strip(),
        "candidates": [
            {
                "text": span.text,
                "lemma": span.lemma,
                "pos": span.pos,
                "reason": span.reason,
            }
            for span in analysis.candidates
        ],
        "groups": _groups_payload(groups),
    }

    output = await run_structured_role(
        "editor",
        variables,
        user_id=user_id,
        output_model=EditorOutput,
        session=session,
        settings=settings,
    )
    assert isinstance(output, EditorOutput)

    newest = session.scalars(
        select(LlmCall)
        .where(LlmCall.user_id == user_id, LlmCall.role == "editor")
        .order_by(LlmCall.created_at.desc())
    ).first()
    llm_call_id = newest.id if newest else None

    run = EditorRun(
        message_id=message_id,
        user_id=user_id,
        llm_call_id=llm_call_id,
        output=output.model_dump(),
    )
    session.add(run)
    session.flush()

    max_n = settings.editor_max_suggestions
    saved: list[Suggestion] = []
    for raw in output.suggestions:
        anchored = _persist_suggestion(
            session,
            run=run,
            user_id=user_id,
            message_id=message_id,
            message=message,
            raw=raw,
            rank=len(saved),
        )
        if anchored is None:
            continue
        saved.append(anchored)
        if len(saved) >= max_n:
            break

    if record_shown:
        for suggestion in saved:
            record_event(
                session,
                user_id=user_id,
                type="suggestion_shown",
                subject_type="suggestion",
                subject_id=suggestion.id,
                payload=SuggestionShownPayload(group_id=suggestion.group_id),
            )

    session.commit()
    for suggestion in saved:
        session.refresh(suggestion)
    return saved


def _persist_suggestion(
    session: Session,
    *,
    run: EditorRun,
    user_id: str,
    message_id: str,
    message: str,
    raw: EditorSuggestion,
    rank: int,
) -> Suggestion | None:
    span = _find_span(message, raw.original)
    if span is None:
        logger.warning("dropping editor suggestion; original not found: %r", raw.original)
        return None
    start, end = span

    group_id = raw.group_id
    if group_id and session.get(PrecisionGroup, group_id) is None:
        group_id = None

    suggestion = Suggestion(
        editor_run_id=run.id,
        message_id=message_id,
        user_id=user_id,
        original_text=raw.original,
        span_start=start,
        span_end=end,
        group_id=group_id,
        question=raw.question,
        rank=rank,
    )
    session.add(suggestion)
    session.flush()

    for opt_rank, opt in enumerate(raw.options):
        resolved = _resolve_option_id(session, opt.word, opt.option_id, group_id)
        session.add(
            SuggestionOption(
                suggestion_id=suggestion.id,
                option_id=resolved,
                word=opt.word,
                meaning=opt.meaning,
                rank=opt_rank,
            )
        )
        if resolved is None:
            session.add(
                ReviewQueueItem(
                    editor_run_id=run.id,
                    head_lemma=group_id.split(".")[0] if group_id else raw.original,
                    proposed_word=opt.word,
                    distinction=opt.meaning,
                    example="",
                    status="pending",
                )
            )
    return suggestion
