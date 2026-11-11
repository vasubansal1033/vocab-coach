"""Run the editor on a user message and persist anchored suggestions."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings, get_settings
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.editor.schemas import EditorOutput, EditorSuggestion
from vocab.events import SuggestionShownPayload, record_event
from vocab.lexicon.models import PrecisionGroup, PrecisionOption, ReviewQueueItem
from vocab.lexicon.service import approved_groups_for_lemma
from vocab.lexicon.synonym_api import synonym_hints
from vocab.llm.graphs import run_structured_role
from vocab.llm.models import LlmCall
from vocab.nlp.analyzer import analyze
from vocab.nlp.types import Analysis

logger = logging.getLogger(__name__)


async def build_editor_variables(
    session: Session,
    *,
    message: str,
    analysis: Analysis,
    partner_previous: str | None = None,
    conversation_title: str | None = None,
    feedback_expectations: str | None = None,
) -> dict[str, Any]:
    """Assemble prompt variables, including Datamuse synonym hints."""
    lemma_pos: list[tuple[str, str | None]] = [
        (span.lemma, span.pos) for span in analysis.candidates
    ]
    lemma_set = {lemma for lemma, _ in lemma_pos}
    groups: list[PrecisionGroup] = []
    seen_group_ids: set[str] = set()
    for lemma in sorted(lemma_set):
        for group in approved_groups_for_lemma(session, lemma):
            if group.id not in seen_group_ids:
                seen_group_ids.add(group.id)
                groups.append(group)

    hints = await synonym_hints(lemma_pos)
    # Surface lexicon options that match hint words even when head_lemma differs.
    hint_words = sorted({w for words in hints.values() for w in words})
    if hint_words:
        for group in _approved_groups_for_words(session, hint_words):
            if group.id not in seen_group_ids:
                seen_group_ids.add(group.id)
                groups.append(group)
    # Put lexicon-overlapping hints first so the model sees strong options early.
    lexicon_words = {
        opt.word.lower()
        for group in groups
        for opt in group.options
        if opt.status == "approved"
    }
    hints = {
        lemma: sorted(words, key=lambda w: (0 if w in lexicon_words else 1, words.index(w)))
        for lemma, words in hints.items()
    }

    return {
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
        "synonym_hints": hints,
        "groups": _groups_payload(groups),
    }


def _approved_groups_for_words(session: Session, words: list[str]) -> list[PrecisionGroup]:
    """Find approved groups that already list any of these option words."""
    from sqlalchemy import func

    lowered = sorted({w.lower() for w in words})
    if not lowered:
        return []
    options = list(
        session.scalars(
            select(PrecisionOption)
            .where(
                PrecisionOption.status == "approved",
                func.lower(PrecisionOption.word).in_(lowered),
            )
            .options(selectinload(PrecisionOption.group).selectinload(PrecisionGroup.options))
        )
    )
    groups: list[PrecisionGroup] = []
    seen: set[str] = set()
    for opt in options:
        group = opt.group
        # Idioms arrive later via allow_idioms; confusable sets are for Compare.
        if (
            group is None
            or group.status != "approved"
            or group.kind != "precision"
            or group.id in seen
        ):
            continue
        seen.add(group.id)
        group.options = [o for o in group.options if o.status == "approved"]
        groups.append(group)
    return groups


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
    variables = await build_editor_variables(
        session,
        message=message,
        analysis=analysis,
        partner_previous=partner_previous,
        conversation_title=conversation_title,
        feedback_expectations=feedback_expectations,
    )

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
