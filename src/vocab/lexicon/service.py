"""Load, draft, export, and review precision groups."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from vocab.lexicon.models import PrecisionGroup, PrecisionOption, ReviewQueueItem
from vocab.lexicon.schemas import (
    ConfusableGenOutput,
    GroupGenOutput,
    GroupKind,
    GroupSeed,
    IdiomGenOutput,
    LemmaSeedFile,
    OptionSeed,
    validate_details,
)
from vocab.lexicon.wordnet import senses_for_lemma

SEEDS_DIR = Path(__file__).resolve().parents[3] / "data" / "precision_groups"


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


def load_seeds(session: Session, *, seeds_dir: Path | None = None) -> dict[str, int]:
    """Upsert YAML seeds as approved; safe to rerun."""
    directory = seeds_dir or SEEDS_DIR
    group_count = 0
    option_count = 0
    for path in sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        seed = LemmaSeedFile.model_validate(raw)
        for group_data in seed.groups:
            _upsert_group(
                session,
                group_id=group_data.id,
                kind=seed.kind,
                head_lemma=seed.head_lemma,
                pos=group_data.pos,
                sense_gloss=group_data.sense_gloss,
                status="approved",
                source="seed",
            )
            group_count += 1
            for opt in group_data.options:
                _upsert_option(session, group_id=group_data.id, opt=opt, status="approved")
                option_count += 1

    session.commit()
    return {"groups": group_count, "options": option_count}


def counts(session: Session) -> dict[str, int]:
    """Row counts for idempotency checks."""
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


def _option_payload(opt: PrecisionOption) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "word": opt.word,
        "distinction": opt.distinction,
        "example": opt.example,
        "register": opt.register,
    }
    if opt.details:
        payload["details"] = opt.details
    return payload


def _group_export_payload(group: PrecisionGroup) -> dict[str, Any]:
    options = [
        _option_payload(opt)
        for opt in sorted(group.options, key=lambda o: o.id)
        if opt.status == "approved"
    ]
    return {
        "id": group.id,
        "pos": group.pos,
        "sense_gloss": group.sense_gloss,
        "options": options,
    }


def export_approved(session: Session, *, seeds_dir: Path | None = None) -> list[Path]:
    """Write approved groups back to YAML, preserving kind and details."""
    directory = seeds_dir or SEEDS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    stmt = (
        select(PrecisionGroup)
        .where(PrecisionGroup.status == "approved")
        .options(selectinload(PrecisionGroup.options))
    )
    precision_by_lemma: dict[str, list[PrecisionGroup]] = {}
    idiom_by_lemma: dict[str, list[PrecisionGroup]] = {}
    confusable: list[PrecisionGroup] = []
    for group in session.scalars(stmt):
        if group.kind == "confusable":
            confusable.append(group)
        elif group.kind == "idiom":
            key = group.head_lemma or group.id
            idiom_by_lemma.setdefault(key, []).append(group)
        else:
            key = group.head_lemma or group.id
            precision_by_lemma.setdefault(key, []).append(group)

    written: list[Path] = []
    for lemma, groups in sorted(precision_by_lemma.items()):
        payload: dict[str, Any] = {
            "head_lemma": lemma,
            "groups": [_group_export_payload(g) for g in sorted(groups, key=lambda g: g.id)],
        }
        path = directory / f"{lemma}.yaml"
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written.append(path)

    for lemma, groups in sorted(idiom_by_lemma.items()):
        payload = {
            "kind": "idiom",
            "head_lemma": lemma,
            "groups": [_group_export_payload(g) for g in sorted(groups, key=lambda g: g.id)],
        }
        path = directory / f"idiom.{lemma}.yaml"
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written.append(path)

    for group in sorted(confusable, key=lambda g: g.id):
        payload = {
            "kind": "confusable",
            "groups": [_group_export_payload(group)],
        }
        path = directory / f"{group.id}.yaml"
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        written.append(path)

    return written


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
