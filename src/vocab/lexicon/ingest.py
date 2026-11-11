"""User-facing lexicon list and idempotent batch ingest/import."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from vocab.lexicon.models import LexiconSubmission, PrecisionGroup, PrecisionOption
from vocab.lexicon.schemas import GroupKind, LemmaSeedFile, validate_details
from vocab.lexicon.service import _upsert_group, _upsert_option

MAX_BATCH_ITEMS = 20
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_IMPORT_ITEMS = 200
MAX_PUBLIC_IMPORT_ITEMS = 20_000


class IdempotencyConflictError(ValueError):
    """Same Idempotency-Key reused with a different request body."""


def _request_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def list_approved_groups(
    session: Session,
    *,
    kind: GroupKind | None = None,
    q: str | None = None,
    cursor: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[PrecisionGroup], str | None]:
    """Page through approved groups. Cursor is the last seen group id."""
    page_size = max(1, min(limit, MAX_PAGE_SIZE))
    stmt = (
        select(PrecisionGroup)
        .where(PrecisionGroup.status == "approved")
        .options(selectinload(PrecisionGroup.options))
        .order_by(PrecisionGroup.id.asc())
    )
    if kind is not None:
        stmt = stmt.where(PrecisionGroup.kind == kind)
    if q:
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                PrecisionGroup.id.ilike(needle),
                PrecisionGroup.head_lemma.ilike(needle),
                PrecisionGroup.sense_gloss.ilike(needle),
            )
        )
    if cursor:
        stmt = stmt.where(PrecisionGroup.id > cursor)
    rows = list(session.scalars(stmt.limit(page_size + 1)))
    page = rows[:page_size]
    for group in page:
        group.options = [o for o in group.options if o.status == "approved"]
    next_cursor = page[-1].id if len(rows) > page_size else None
    return page, next_cursor


def get_approved_group(session: Session, group_id: str) -> PrecisionGroup | None:
    """One approved group with approved options, or None."""
    group = session.scalars(
        select(PrecisionGroup)
        .where(PrecisionGroup.id == group_id, PrecisionGroup.status == "approved")
        .options(selectinload(PrecisionGroup.options))
    ).first()
    if group is None:
        return None
    group.options = [o for o in group.options if o.status == "approved"]
    return group


def _allocate_draft_id(session: Session, preferred: str) -> str:
    """Never overwrite an existing row; mint a stable-looking unique draft id."""
    if session.get(PrecisionGroup, preferred) is None:
        return preferred
    return f"{preferred}.user.{uuid4().hex[:8]}"


def _store_user_item(session: Session, item: LemmaSeedFile) -> list[dict[str, str]]:
    created: list[dict[str, str]] = []
    for group_data in item.groups:
        draft_id = _allocate_draft_id(session, group_data.id)
        _upsert_group(
            session,
            group_id=draft_id,
            kind=item.kind,
            head_lemma=item.head_lemma,
            pos=group_data.pos,
            sense_gloss=group_data.sense_gloss,
            status="draft",
            source="user",
        )
        for opt in group_data.options:
            opt.details = validate_details(item.kind, opt.details)
            _upsert_option(session, group_id=draft_id, opt=opt, status="draft")
        created.append(
            {
                "requested_id": group_data.id,
                "stored_id": draft_id,
                "status": "draft",
            }
        )
    return created


def _replay_or_start(
    session: Session,
    *,
    user_id: str,
    idempotency_key: str,
    body: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    key = idempotency_key.strip()
    if not key:
        raise ValueError("Idempotency-Key must not be empty")
    digest = _request_hash(body)
    existing = session.scalars(
        select(LexiconSubmission).where(
            LexiconSubmission.user_id == user_id,
            LexiconSubmission.idempotency_key == key,
        )
    ).first()
    if existing is not None:
        if existing.request_hash != digest:
            raise IdempotencyConflictError(
                "Idempotency-Key already used with a different request body"
            )
        return existing.response, digest
    return None, digest


def _finish_submission(
    session: Session,
    *,
    user_id: str,
    idempotency_key: str,
    request_hash: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    session.add(
        LexiconSubmission(
            user_id=user_id,
            idempotency_key=idempotency_key.strip(),
            request_hash=request_hash,
            response=response,
        )
    )
    session.commit()
    return response


def submit_user_batch(
    session: Session,
    *,
    user_id: str,
    idempotency_key: str,
    items: list[LemmaSeedFile],
) -> dict[str, Any]:
    """Create draft groups from a user batch. Replays when the key matches.

    Raises IdempotencyConflictError when the key is reused with a different body.
    """
    if not items:
        raise ValueError("items must not be empty")
    if len(items) > MAX_BATCH_ITEMS:
        raise ValueError(f"at most {MAX_BATCH_ITEMS} items per batch")

    body = {"items": [item.model_dump(by_alias=True) for item in items]}
    replay, digest = _replay_or_start(
        session, user_id=user_id, idempotency_key=idempotency_key, body=body
    )
    if replay is not None:
        return replay

    results: list[dict[str, str]] = []
    for item in items:
        results.extend(_store_user_item(session, item))

    response = {
        "idempotency_key": idempotency_key.strip(),
        "created": results,
        "count": len(results),
    }
    return _finish_submission(
        session,
        user_id=user_id,
        idempotency_key=idempotency_key,
        request_hash=digest,
        response=response,
    )


def import_approved_items(
    session: Session,
    items: list[LemmaSeedFile],
    *,
    source: str = "api",
) -> dict[str, int]:
    """Upsert items as approved. Used by admin import APIs and tests."""
    if not items:
        raise ValueError("items must not be empty")
    if len(items) > MAX_IMPORT_ITEMS:
        raise ValueError(f"at most {MAX_IMPORT_ITEMS} items per import")
    group_count = 0
    option_count = 0
    for item in items:
        for group_data in item.groups:
            _upsert_group(
                session,
                group_id=group_data.id,
                kind=item.kind,
                head_lemma=item.head_lemma,
                pos=group_data.pos,
                sense_gloss=group_data.sense_gloss,
                status="approved",
                source=source,
            )
            group_count += 1
            for opt in group_data.options:
                opt.details = validate_details(item.kind, opt.details)
                _upsert_option(session, group_id=group_data.id, opt=opt, status="approved")
                option_count += 1
    session.commit()
    return {"groups": group_count, "options": option_count}


def import_approved_batch(
    session: Session,
    *,
    user_id: str,
    idempotency_key: str,
    items: list[LemmaSeedFile],
    source: str = "api",
) -> dict[str, Any]:
    """Admin idempotent approved import from a JSON batch body."""
    body = {"mode": "approved", "items": [item.model_dump(by_alias=True) for item in items]}
    replay, digest = _replay_or_start(
        session, user_id=user_id, idempotency_key=idempotency_key, body=body
    )
    if replay is not None:
        return replay
    counts = import_approved_items(session, items, source=source)
    response = {
        "idempotency_key": idempotency_key.strip(),
        "mode": "approved",
        "groups": counts["groups"],
        "options": counts["options"],
    }
    # import_approved_items already committed; store replay row in a new commit.
    session.add(
        LexiconSubmission(
            user_id=user_id,
            idempotency_key=idempotency_key.strip(),
            request_hash=digest,
            response=response,
        )
    )
    session.commit()
    return response


def import_builtin_catalog(session: Session, *, source: str = "seed") -> dict[str, int]:
    """Load the built-in Python catalog as approved groups (admin/bootstrap)."""
    from vocab.lexicon.builtin_catalog import BUILTIN_LEXICON_ITEMS

    items = [LemmaSeedFile.model_validate(raw) for raw in BUILTIN_LEXICON_ITEMS]
    return import_approved_items(session, items, source=source)


def import_public_catalog(
    session: Session,
    *,
    sources: list[str] | None = None,
    abc_confusable_limit: int | None = None,
    source: str = "public",
) -> dict[str, Any]:
    """Fetch public datasets, convert, and upsert as approved."""
    from vocab.lexicon.public_datasets import (
        SourceName,
        attribution_lines,
        build_public_items,
    )

    allowed: set[str] = {"lexkite", "abc_precision", "abc_confusable"}
    chosen: list[SourceName]
    if sources:
        unknown = [s for s in sources if s not in allowed]
        if unknown:
            raise ValueError(f"unknown sources: {', '.join(unknown)}")
        chosen = [s for s in sources if s in allowed]  # type: ignore[misc]
    else:
        chosen = ["lexkite", "abc_precision", "abc_confusable"]
    items = build_public_items(chosen, abc_confusable_limit=abc_confusable_limit)
    if len(items) > MAX_PUBLIC_IMPORT_ITEMS:
        raise ValueError(f"at most {MAX_PUBLIC_IMPORT_ITEMS} items per public import")
    # Bypass the smaller JSON-body import cap used by /lexicon/import.
    if not items:
        raise ValueError("public import produced no items")
    group_count = 0
    option_count = 0
    for item in items:
        for group_data in item.groups:
            _upsert_group(
                session,
                group_id=group_data.id,
                kind=item.kind,
                head_lemma=item.head_lemma,
                pos=group_data.pos,
                sense_gloss=group_data.sense_gloss,
                status="approved",
                source=source,
            )
            group_count += 1
            for opt in group_data.options:
                opt.details = validate_details(item.kind, opt.details)
                _upsert_option(session, group_id=group_data.id, opt=opt, status="approved")
                option_count += 1
        if group_count % 500 == 0:
            session.flush()
    session.commit()
    return {
        "groups": group_count,
        "options": option_count,
        "items": len(items),
        "sources": list(chosen or ["lexkite", "abc_precision", "abc_confusable"]),
        "attribution": attribution_lines(),
    }


def lexicon_counts(session: Session) -> dict[str, int]:
    """Row counts for checks after import."""
    return {
        "groups": session.scalar(select(func.count()).select_from(PrecisionGroup)) or 0,
        "options": session.scalar(select(func.count()).select_from(PrecisionOption)) or 0,
    }
