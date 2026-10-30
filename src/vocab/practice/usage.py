"""Detect learned-word uses in user messages and update SRS."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vocab.config import Settings, get_settings
from vocab.conversation.models import Message
from vocab.editor.models import Suggestion
from vocab.events import WordUsedPayload, record_event
from vocab.lexicon.models import PrecisionOption
from vocab.nlp.analyzer import analyze
from vocab.nlp.usage import find_learned_words
from vocab.practice.judge import judge_usage
from vocab.practice.srs import learned_option_rows, review_card


def _lemma_in_text(lemma: str, text: str) -> bool:
    """Rough surface check: lemma or its letters as a word in the text."""
    lower = text.lower()
    needle = lemma.lower()
    if needle in lower:
        return True
    # Multi-word: all parts present.
    return all(part in lower for part in needle.split())


def is_prompted(
    session: Session,
    *,
    user_id: str,
    conversation_id: str,
    lemma: str,
    word: str,
) -> bool:
    """True when the lemma showed up in recent partner text or shown suggestions."""
    partner_msgs = session.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id,
            Message.role == "partner",
        )
        .order_by(Message.created_at.desc())
        .limit(3)
    ).all()
    for msg in partner_msgs:
        if _lemma_in_text(lemma, msg.content) or _lemma_in_text(word, msg.content):
            return True

    user_msgs = session.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.user_id == user_id,
            Message.role == "user",
        )
        .order_by(Message.created_at.desc())
        .limit(5)
    ).all()
    message_ids = [m.id for m in user_msgs]
    if not message_ids:
        return False
    suggestions = session.scalars(
        select(Suggestion)
        .where(Suggestion.message_id.in_(message_ids), Suggestion.user_id == user_id)
        .options(selectinload(Suggestion.options))
    ).all()
    for suggestion in suggestions:
        if _lemma_in_text(lemma, suggestion.original_text) or _lemma_in_text(
            word, suggestion.original_text
        ):
            return True
        for opt in suggestion.options:
            if _lemma_in_text(lemma, opt.word) or opt.word.lower() == word.lower():
                return True
    return False


def _options_by_word(options: list[PrecisionOption]) -> dict[str, PrecisionOption]:
    return {opt.word.lower(): opt for opt in options}


async def process_message_usage(
    session: Session,
    *,
    user_id: str,
    conversation_id: str,
    message: Message,
    settings: Settings | None = None,
) -> list[dict[str, object]]:
    """Find learned options in a user message; judge, record, and maybe review."""
    settings = settings or get_settings()
    learned = learned_option_rows(session, user_id)
    if not learned:
        return []
    by_word = _options_by_word(learned)
    lemmas = [opt.word for opt in learned]
    analysis = analyze(message.content)
    hits = find_learned_words(analysis, lemmas)
    results: list[dict[str, object]] = []
    seen_options: set[str] = set()
    for hit in hits:
        opt = by_word.get(hit.lemma.lower()) or by_word.get(hit.text.lower())
        if opt is None:
            # PhraseMatcher returns the pattern string as lemma.
            for candidate in learned:
                if candidate.word.lower() == hit.lemma.lower():
                    opt = candidate
                    break
        if opt is None or opt.id in seen_options:
            continue
        seen_options.add(opt.id)
        prompted = is_prompted(
            session,
            user_id=user_id,
            conversation_id=conversation_id,
            lemma=hit.lemma,
            word=opt.word,
        )
        judge_call_id: str | None = None
        correct = True
        if not prompted:
            judged, judge_call_id = await judge_usage(
                session,
                user_id=user_id,
                sentence=message.content,
                word=opt.word,
                distinction=opt.distinction,
                settings=settings,
            )
            correct = judged.correct
        record_event(
            session,
            user_id=user_id,
            type="word_used",
            subject_type="message",
            subject_id=message.id,
            payload=WordUsedPayload(
                option_id=opt.id,
                correct=correct,
                prompted=prompted,
                judge_call_id=judge_call_id,
            ),
        )
        if not prompted:
            review_card(
                session,
                user_id=user_id,
                option_id=opt.id,
                rating="Good" if correct else "Again",
                source="conversation",
            )
        else:
            session.commit()
        results.append(
            {
                "option_id": opt.id,
                "word": opt.word,
                "prompted": prompted,
                "correct": correct,
            }
        )
    return results
