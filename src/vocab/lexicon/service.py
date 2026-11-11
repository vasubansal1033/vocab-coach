"""Draft, review, and query precision groups (DB is the source of truth)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from vocab.lexicon.models import PrecisionGroup, PrecisionOption, ReviewQueueItem
from vocab.lexicon.schemas import (
    ConfusableGenOutput,
    GroupGenOutput,
    GroupKind,
    GroupSeed,
    IdiomGenOutput,
    OptionSeed,
    validate_details,
)
from vocab.lexicon.wordnet import senses_for_lemma


def option_id(group_id: str, word: str) -> str:
    """Stable id used across seeds, DB, and events."""
    return f"{group_id}/{word}"


def _upsert_group(
    session: Session,
    *,
    group_id: str,
    kind: GroupKind,
    head_lemma: str | None,
    pos: str,
    sense_gloss: str,
    status: str,
    source: str,
) -> PrecisionGroup:
    group = session.get(PrecisionGroup, group_id)
    if group is None:
        group = PrecisionGroup(
            id=group_id,
            kind=kind,
            head_lemma=head_lemma,
            pos=pos,
            sense_gloss=sense_gloss,
            status=status,
            source=source,
        )
        session.add(group)
    else:
        group.kind = kind
        group.head_lemma = head_lemma
        group.pos = pos
        group.sense_gloss = sense_gloss
        group.status = status
        group.source = source
    return group


def _upsert_option(
    session: Session,
    *,
    group_id: str,
    opt: OptionSeed,
    status: str,
) -> None:
    oid = option_id(group_id, opt.word)
    existing = session.get(PrecisionOption, oid)
    if existing is None:
        session.add(
            PrecisionOption(
                id=oid,
                group_id=group_id,
                word=opt.word,
                distinction=opt.distinction,
                example=opt.example,
                register=opt.speech_register,
                status=status,
                details=opt.details,
            )
        )
    else:
        existing.word = opt.word
        existing.distinction = opt.distinction
        existing.example = opt.example
        existing.register = opt.speech_register
        existing.status = status
        existing.group_id = group_id
        existing.details = opt.details


def counts(session: Session) -> dict[str, int]:
    """Row counts for checks after import."""
    return {
        "groups": session.scalar(select(func.count()).select_from(PrecisionGroup)) or 0,
        "options": session.scalar(select(func.count()).select_from(PrecisionOption)) or 0,
    }


def approved_groups_for_lemma(
    session: Session,
    lemma: str,
    *,
    kinds: tuple[GroupKind, ...] = ("precision",),
) -> list[PrecisionGroup]:
    """Groups the editor may use for a candidate lemma; defaults to precision only."""
    stmt = (
        select(PrecisionGroup)
        .where(
            PrecisionGroup.head_lemma == lemma,
            PrecisionGroup.status == "approved",
            PrecisionGroup.kind.in_(kinds),
        )
        .options(selectinload(PrecisionGroup.options))
    )
    groups = list(session.scalars(stmt))
    for group in groups:
        group.options = [o for o in group.options if o.status == "approved"]
    return groups


def _store_draft_groups(
    session: Session,
    *,
    kind: GroupKind,
    head_lemma: str | None,
    groups: list[GroupSeed],
) -> list[PrecisionGroup]:
    created: list[PrecisionGroup] = []
    for group_data in groups:
        existing = session.get(PrecisionGroup, group_data.id)
        if existing is not None and existing.status == "approved":
            # Never overwrite an approved seed with a draft of the same id.
            draft_id = f"{group_data.id}.draft"
        else:
            draft_id = group_data.id
        _upsert_group(
            session,
            group_id=draft_id,
            kind=kind,
            head_lemma=head_lemma,
            pos=group_data.pos,
            sense_gloss=group_data.sense_gloss,
            status="draft",
            source="llm",
        )
        for opt in group_data.options:
            opt.details = validate_details(kind, opt.details)
            _upsert_option(session, group_id=draft_id, opt=opt, status="draft")
        group = session.get(PrecisionGroup, draft_id)
        assert group is not None
        created.append(group)
    session.commit()
    for group in created:
        session.refresh(group)
    return created


async def draft_lemma(
    session: Session,
    lemma: str,
    *,
    user_id: str | None = None,
) -> list[PrecisionGroup]:
    """Ask group_gen for draft groups and store them as draft/llm."""
    from vocab.llm.graphs import run_structured_role

    senses = senses_for_lemma(lemma)
    result = await run_structured_role(
        "group_gen",
        {"lemma": lemma, "senses": senses},
        user_id=user_id,
        output_model=GroupGenOutput,
        session=session,
    )
    assert isinstance(result, GroupGenOutput)
    return _store_draft_groups(
        session,
        kind="precision",
        head_lemma=result.head_lemma or lemma,
        groups=result.groups,
    )


async def draft_set(
    session: Session,
    kind: Literal["confusable", "idiom"],
    *,
    words: list[str] | None = None,
    lemma: str | None = None,
    user_id: str | None = None,
) -> list[PrecisionGroup]:
    """Ask confusable_gen or idiom_gen for draft sets and store them as draft/llm."""
    from vocab.llm.graphs import run_structured_role

    if kind == "confusable":
        if not words:
            raise ValueError("confusable drafts need --words")
        result = await run_structured_role(
            "confusable_gen",
            {"words": words},
            user_id=user_id,
            output_model=ConfusableGenOutput,
            session=session,
        )
        assert isinstance(result, ConfusableGenOutput)
        return _store_draft_groups(
            session,
            kind="confusable",
            head_lemma=None,
            groups=result.groups,
        )

    if not lemma:
        raise ValueError("idiom drafts need --lemma")
    result = await run_structured_role(
        "idiom_gen",
        {"lemma": lemma},
        user_id=user_id,
        output_model=IdiomGenOutput,
        session=session,
    )
    assert isinstance(result, IdiomGenOutput)
    return _store_draft_groups(
        session,
        kind="idiom",
        head_lemma=result.head_lemma or lemma,
        groups=result.groups,
    )


def approve_group(session: Session, group_id: str) -> PrecisionGroup:
    """Mark a draft group and its options approved."""
    group = session.get(PrecisionGroup, group_id)
    if group is None:
        raise KeyError(group_id)
    group.status = "approved"
    for opt in group.options:
        opt.status = "approved"
    session.commit()
    session.refresh(group)
    return group


def reject_group(session: Session, group_id: str) -> None:
    """Delete a draft group (and options via cascade)."""
    group = session.get(PrecisionGroup, group_id)
    if group is None:
        raise KeyError(group_id)
    session.delete(group)
    session.commit()


def update_group(
    session: Session,
    group_id: str,
    *,
    sense_gloss: str,
    options: list[dict[str, str]],
) -> PrecisionGroup:
    """Edit a draft group's gloss and options before approve."""
    group = session.get(PrecisionGroup, group_id)
    if group is None:
        raise KeyError(group_id)
    group.sense_gloss = sense_gloss
    keep: set[str] = set()
    for opt in options:
        word = opt["word"].strip()
        if not word:
            continue
        oid = option_id(group_id, word)
        keep.add(oid)
        row = session.get(PrecisionOption, oid)
        if row is None:
            session.add(
                PrecisionOption(
                    id=oid,
                    group_id=group_id,
                    word=word,
                    distinction=opt.get("distinction", ""),
                    example=opt.get("example", ""),
                    register=opt.get("register", "neutral"),
                    status=group.status,
                    details=None,
                )
            )
        else:
            row.distinction = opt.get("distinction", "")
            row.example = opt.get("example", "")
            row.register = opt.get("register", "neutral")
    for row in list(group.options):
        if row.id not in keep:
            session.delete(row)
    session.commit()
    session.refresh(group)
    return group


def list_drafts(session: Session) -> list[PrecisionGroup]:
    stmt = (
        select(PrecisionGroup)
        .where(PrecisionGroup.status == "draft")
        .options(selectinload(PrecisionGroup.options))
        .order_by(PrecisionGroup.created_at.desc())
    )
    return list(session.scalars(stmt))


def list_approved(session: Session) -> list[PrecisionGroup]:
    """Approved sets for the admin page, including confusable and idiom."""
    stmt = (
        select(PrecisionGroup)
        .where(PrecisionGroup.status == "approved")
        .options(selectinload(PrecisionGroup.options))
        .order_by(PrecisionGroup.kind, PrecisionGroup.id)
    )
    return list(session.scalars(stmt))


def list_review_queue(session: Session) -> list[ReviewQueueItem]:
    stmt = (
        select(ReviewQueueItem)
        .where(ReviewQueueItem.status == "pending")
        .order_by(ReviewQueueItem.created_at.desc())
    )
    return list(session.scalars(stmt))


def reject_review_item(session: Session, item_id: str) -> None:
    item = session.get(ReviewQueueItem, item_id)
    if item is None:
        raise KeyError(item_id)
    item.status = "rejected"
    session.commit()


def approve_review_item(session: Session, item_id: str) -> ReviewQueueItem:
    """Mark a queue item approved; attaching to a group is a later editor step."""
    item = session.get(ReviewQueueItem, item_id)
    if item is None:
        raise KeyError(item_id)
    item.status = "approved"
    session.commit()
    session.refresh(item)
    return item
