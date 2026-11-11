"""Conversation CRUD, message save, accept/dismiss, retry, recap."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from vocab.conversation.models import Conversation, Message, MessageLemmaCount
from vocab.editor.models import EditorRun, Suggestion, SuggestionOption
from vocab.events import (
    Event,
    SuggestionAcceptedPayload,
    SuggestionRetriedPayload,
    record_event,
)
from vocab.lexicon.models import ReviewQueueItem
from vocab.nlp.analyzer import analyze
from vocab.nlp.crutch import crutch_entries, is_crutch
from vocab.nlp.persist import lemma_count_rows, word_count_value


def list_conversations(session: Session, user_id: str) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(session.scalars(stmt))


def get_conversation(session: Session, conversation_id: str) -> Conversation | None:
    return session.scalars(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    ).first()


def create_conversation(
    session: Session,
    user_id: str,
    name: str,
    *,
    feedback_expectations: str | None = None,
    flow_mode: bool = False,
    allow_idioms: bool = False,
) -> Conversation:
    """Start a thread; flow_mode and allow_idioms are fixed at creation."""
    brief = (feedback_expectations or "").strip() or None
    conversation = Conversation(
        user_id=user_id,
        title=name.strip() or "Conversation",
        feedback_expectations=brief,
        flow_mode=bool(flow_mode),
        allow_idioms=bool(allow_idioms),
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    return conversation


def delete_conversation(session: Session, conversation: Conversation) -> None:
    """Remove one conversation and its message-linked editor rows. Keep events for metrics.

    Caller must authorize ownership before calling.
    """
    message_ids = list(
        session.scalars(select(Message.id).where(Message.conversation_id == conversation.id))
    )
    if message_ids:
        run_ids = list(
            session.scalars(select(EditorRun.id).where(EditorRun.message_id.in_(message_ids)))
        )
        suggestion_ids = list(
            session.scalars(select(Suggestion.id).where(Suggestion.message_id.in_(message_ids)))
        )
        if suggestion_ids:
            session.execute(
                delete(SuggestionOption).where(
                    SuggestionOption.suggestion_id.in_(suggestion_ids)
                )
            )
        session.execute(delete(Suggestion).where(Suggestion.message_id.in_(message_ids)))
        if run_ids:
            # review_queue.editor_run_id FK blocks editor_runs deletes.
            session.execute(
                delete(ReviewQueueItem).where(ReviewQueueItem.editor_run_id.in_(run_ids))
            )
            session.execute(delete(EditorRun).where(EditorRun.id.in_(run_ids)))
        session.execute(
            delete(MessageLemmaCount).where(MessageLemmaCount.message_id.in_(message_ids))
        )
        session.execute(delete(Message).where(Message.id.in_(message_ids)))
    session.execute(delete(Conversation).where(Conversation.id == conversation.id))
    session.commit()


def post_user_message(
    session: Session,
    *,
    conversation: Conversation,
    user_id: str,
    content: str,
) -> Message:
    """Store a user message and its lemma counts."""
    text = content.strip()
    analysis = analyze(text)
    message = Message(
        conversation_id=conversation.id,
        user_id=user_id,
        role="user",
        content=text,
        word_count=word_count_value(analysis),
    )
    session.add(message)
    session.flush()
    for row in lemma_count_rows(analysis):
        session.add(
            MessageLemmaCount(
                message_id=message.id,
                user_id=user_id,
                lemma=row["lemma"],
                surface=row["surface"],
                count=row["count"],
            )
        )
    session.commit()
    session.refresh(message)
    return message


def save_partner_message(
    session: Session,
    *,
    conversation_id: str,
    user_id: str,
    content: str,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="partner",
        content=content,
        word_count=0,
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message


def chat_history(session: Session, conversation_id: str) -> list[dict[str, str]]:
    """Prior turns as LiteLLM chat messages (user/assistant)."""
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    history: list[dict[str, str]] = []
    for msg in messages:
        role = "user" if msg.role == "user" else "assistant"
        history.append({"role": role, "content": msg.content})
    return history


def previous_partner_content(session: Session, conversation_id: str) -> str | None:
    msg = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id, Message.role == "partner")
        .order_by(Message.created_at.desc())
    ).first()
    return msg.content if msg else None


def accept_suggestion(
    session: Session,
    *,
    suggestion: Suggestion,
    option: SuggestionOption,
    user_id: str,
) -> Suggestion:
    """Record acceptance once; retry and a later Accept click must not double-count."""
    if not _suggestion_has_event(
        session, user_id=user_id, suggestion_id=suggestion.id, event_type="suggestion_accepted"
    ):
        record_event(
            session,
            user_id=user_id,
            type="suggestion_accepted",
            subject_type="suggestion",
            subject_id=suggestion.id,
            payload=SuggestionAcceptedPayload(option_id=option.option_id, word=option.word),
        )
        session.commit()
    if option.option_id:
        from vocab.practice.srs import ensure_card

        ensure_card(session, user_id=user_id, option_id=option.option_id)
    return suggestion


def dismiss_suggestion(
    session: Session,
    *,
    suggestion: Suggestion,
    user_id: str,
) -> Suggestion:
    record_event(
        session,
        user_id=user_id,
        type="suggestion_dismissed",
        subject_type="suggestion",
        subject_id=suggestion.id,
        payload=None,
    )
    session.commit()
    return suggestion


def _suggestion_has_event(
    session: Session, *, user_id: str, suggestion_id: str, event_type: str
) -> bool:
    return (
        session.scalars(
            select(Event.id).where(
                Event.user_id == user_id,
                Event.type == event_type,
                Event.subject_type == "suggestion",
                Event.subject_id == suggestion_id,
            )
        ).first()
        is not None
    )


def retry_suggestion(
    session: Session,
    *,
    suggestion: Suggestion,
    option: SuggestionOption,
    user_id: str,
) -> str:
    """Replace the suggestion span with the option word and accept once if needed.

    Returns the rewritten message text for the frontend draft box.
    """
    message = session.get(Message, suggestion.message_id)
    if message is None:
        raise ValueError("suggestion message missing")
    content = message.content
    start = suggestion.span_start
    end = suggestion.span_end
    if start < 0 or end > len(content) or start > end:
        raise ValueError("suggestion span out of range")
    rewritten = content[:start] + option.word + content[end:]
    record_event(
        session,
        user_id=user_id,
        type="suggestion_retried",
        subject_type="suggestion",
        subject_id=suggestion.id,
        payload=SuggestionRetriedPayload(option_id=option.option_id, word=option.word),
    )
    session.commit()
    # Accept once (idempotent) so the card and acceptance rate stay correct.
    accept_suggestion(session, suggestion=suggestion, option=option, user_id=user_id)
    return rewritten


@dataclass(frozen=True)
class RecapWord:
    word: str
    option_id: str | None
    source: str


@dataclass(frozen=True)
class RecapCrutch:
    lemma: str
    count: int


@dataclass(frozen=True)
class ConversationRecap:
    words_to_keep: list[RecapWord]
    crutch_words: list[RecapCrutch]
    rewrite_sentence: str | None


def _lemma_is_crutch(lemma: str) -> bool:
    """True when the lemma is on the crutch list for any POS (counts store no POS)."""
    lower = lemma.lower()
    return any(
        is_crutch(lower, pos)
        for entry_lemma, pos in crutch_entries()
        if entry_lemma == lower
    )


def _sentence_at_offset(text: str, char_offset: int) -> str:
    """Sentence containing char_offset, using spaCy sentence boundaries."""
    analysis = analyze(text)
    for sent in analysis.doc.sents:
        if sent.start_char <= char_offset < sent.end_char:
            return sent.text.strip()
    return text.strip()


def _conversation_suggestions(
    session: Session, *, conversation_id: str, user_id: str
) -> list[Suggestion]:
    message_ids = list(
        session.scalars(
            select(Message.id).where(
                Message.conversation_id == conversation_id,
                Message.user_id == user_id,
                Message.role == "user",
            )
        )
    )
    if not message_ids:
        return []
    return list(
        session.scalars(
            select(Suggestion)
            .where(Suggestion.message_id.in_(message_ids), Suggestion.user_id == user_id)
            .options(selectinload(Suggestion.options))
            .order_by(Suggestion.rank.asc())
        )
    )


async def conversation_recap(
    session: Session,
    *,
    conversation: Conversation,
    user_id: str,
    settings: object | None = None,
) -> ConversationRecap:
    """Build a recap from recorded data; in flow mode run the editor first for each message."""
    from vocab.config import Settings, get_settings
    from vocab.conversation.feedback import ensure_message_feedback

    cfg: Settings = settings if isinstance(settings, Settings) else get_settings()

    user_messages = list(
        session.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.user_id == user_id,
                Message.role == "user",
            )
            .order_by(Message.created_at.asc())
        )
    )
    # Flow mode defers the editor until now so suggestion_shown does not fire early.
    for message in user_messages:
        existing = session.scalars(
            select(EditorRun.id).where(
                EditorRun.message_id == message.id, EditorRun.user_id == user_id
            )
        ).first()
        if existing is None:
            await ensure_message_feedback(
                session,
                conversation=conversation,
                message=message,
                user_id=user_id,
                settings=cfg,
                allow_flow_mode=True,
            )

    suggestions = _conversation_suggestions(
        session, conversation_id=conversation.id, user_id=user_id
    )
    accepted_ids: set[str] = set()
    dismissed_ids: set[str] = set()
    shown_ids: set[str] = set()
    if suggestions:
        suggestion_ids = [s.id for s in suggestions]
        for event in session.scalars(
            select(Event).where(
                Event.user_id == user_id,
                Event.subject_type == "suggestion",
                Event.subject_id.in_(suggestion_ids),
                Event.type.in_(
                    ("suggestion_accepted", "suggestion_dismissed", "suggestion_shown")
                ),
            )
        ):
            if event.type == "suggestion_accepted":
                accepted_ids.add(event.subject_id)
            elif event.type == "suggestion_dismissed":
                dismissed_ids.add(event.subject_id)
            elif event.type == "suggestion_shown":
                shown_ids.add(event.subject_id)

    words_to_keep: list[RecapWord] = []
    seen_words: set[str] = set()

    # Accepted options first (order by suggestion rank).
    for suggestion in suggestions:
        if suggestion.id not in accepted_ids:
            continue
        accepted_events = list(
            session.scalars(
                select(Event).where(
                    Event.user_id == user_id,
                    Event.type == "suggestion_accepted",
                    Event.subject_id == suggestion.id,
                )
            )
        )
        for event in accepted_events:
            word = str(event.payload.get("word") or "").strip()
            if not word or word.lower() in seen_words:
                continue
            seen_words.add(word.lower())
            words_to_keep.append(
                RecapWord(
                    word=word,
                    option_id=event.payload.get("option_id"),
                    source="accepted",
                )
            )
            if len(words_to_keep) >= 3:
                break
        if len(words_to_keep) >= 3:
            break

    # Then highest-ranked shown and not dismissed options.
    if len(words_to_keep) < 3:
        for suggestion in suggestions:
            if suggestion.id not in shown_ids or suggestion.id in dismissed_ids:
                continue
            for opt in sorted(suggestion.options, key=lambda o: o.rank):
                key = opt.word.lower()
                if key in seen_words:
                    continue
                seen_words.add(key)
                words_to_keep.append(
                    RecapWord(word=opt.word, option_id=opt.option_id, source="shown")
                )
                if len(words_to_keep) >= 3:
                    break
            if len(words_to_keep) >= 3:
                break

    # Crutch lemmas from stored counts, filtered with is_crutch().
    message_ids = [m.id for m in user_messages]
    crutch_totals: dict[str, int] = defaultdict(int)
    if message_ids:
        for row in session.scalars(
            select(MessageLemmaCount).where(
                MessageLemmaCount.message_id.in_(message_ids),
                MessageLemmaCount.user_id == user_id,
            )
        ):
            if _lemma_is_crutch(row.lemma):
                crutch_totals[row.lemma] += row.count
    crutch_words = [
        RecapCrutch(lemma=lemma, count=count)
        for lemma, count in sorted(crutch_totals.items(), key=lambda item: (-item[1], item[0]))
    ]

    # One sentence from the highest-ranked open (neither accepted nor dismissed) suggestion.
    rewrite_sentence: str | None = None
    messages_by_id = {m.id: m for m in user_messages}
    for suggestion in suggestions:
        if suggestion.id in accepted_ids or suggestion.id in dismissed_ids:
            continue
        message = messages_by_id.get(suggestion.message_id)
        if message is None:
            continue
        rewrite_sentence = _sentence_at_offset(message.content, suggestion.span_start)
        break

    return ConversationRecap(
        words_to_keep=words_to_keep,
        crutch_words=crutch_words,
        rewrite_sentence=rewrite_sentence,
    )
