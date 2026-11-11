"""Choose which precision group a new drill should target."""

from __future__ import annotations

import random
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from wordfreq import word_frequency

from vocab.conversation.models import MessageLemmaCount
from vocab.lexicon.models import PrecisionGroup, PrecisionOption
from vocab.practice.models import SrsCard, utcnow
from vocab.practice.srs import due_options


def _approved_groups(session: Session) -> list[PrecisionGroup]:
    """Rewrite drills only target precision groups, never confusable or idiom sets."""
    return list(
        session.scalars(
            select(PrecisionGroup)
            .where(
                PrecisionGroup.status == "approved",
                PrecisionGroup.kind == "precision",
            )
            .options(selectinload(PrecisionGroup.options))
        )
    )


def _overuse_head_lemmas(session: Session, user_id: str, *, limit: int = 10) -> list[str]:
    """Surface words the user overuses vs English frequency; map later to groups."""
    rows = session.scalars(
        select(MessageLemmaCount).where(MessageLemmaCount.user_id == user_id)
    ).all()
    if not rows:
        return []
    totals: dict[str, int] = defaultdict(int)
    surfaces: dict[str, str] = {}
    for row in rows:
        key = row.surface.lower()
        totals[key] += row.count
        surfaces[key] = row.surface
    total_words = sum(totals.values()) or 1
    lifts: list[tuple[float, str]] = []
    for key, count in totals.items():
        if count < 5:
            continue
        freq = word_frequency(key, "en") or 1e-9
        lift = (count / total_words) / freq
        lifts.append((lift, surfaces[key]))
    lifts.sort(reverse=True)
    return [surface for _lift, surface in lifts[:limit]]


def select_group(session: Session, user_id: str) -> PrecisionGroup:
    """Prefer due-card groups, then overuse heads, then random approved."""
    groups = _approved_groups(session)
    if not groups:
        raise RuntimeError("no approved precision groups; run vocab lexicon load")

    by_id = {g.id: g for g in groups}
    by_lemma: defaultdict[str, list[PrecisionGroup]] = defaultdict(list)
    for group in groups:
        if group.head_lemma:
            by_lemma[group.head_lemma.lower()].append(group)

    # 1) Due cards → their option's group.
    for opt in due_options(session, user_id, limit=5):
        group = by_id.get(opt.group_id)
        if group is not None:
            return group

    # Also any due card's group via option join if due_options empty of match.
    now = utcnow()
    due_cards = session.scalars(
        select(SrsCard).where(SrsCard.user_id == user_id, SrsCard.due_at <= now)
    ).all()
    for card in due_cards:
        opt = session.get(PrecisionOption, card.option_id)
        if opt and opt.group_id in by_id:
            return by_id[opt.group_id]

    # 2) Overuse lift → groups whose head_lemma matches a surface/lemma.
    for surface in _overuse_head_lemmas(session, user_id):
        candidates = by_lemma.get(surface.lower())
        if candidates:
            return candidates[0]

    # 3) Random approved group.
    return random.choice(groups)
