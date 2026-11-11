"""Seed two weeks of messages/events with hand-known metric values.

Window: [ANCHOR - 14d, ANCHOR) with ANCHOR = 2026-11-10 12:00 UTC.

Week buckets (ISO weeks ending at ANCHOR):
  week_old  = [ANCHOR-14d, ANCHOR-7d)
  week_new  = [ANCHOR-7d, ANCHOR)

Messages (user role only):
  week_old: word_count=10, lemma_counts fix×2, hard×1, thing×3  → crutch hits 6
  week_new: word_count=10, lemma_counts fix×1, big×1, thing×2  → crutch hits 4

Total words=20. Crutch lemma hits = fix(3)+hard(1)+big(1)+thing(5)=10.
  crutch_rate overall = 1000*10/20 = 500
  crutch_rate fix = 1000*3/20 = 150
  week_old rate = 600; week_new rate = 400

thing surface count=5 → overuse lift = (5/20)/word_frequency('thing')

Events:
  4 suggestion_shown, 2 suggestion_accepted (fix.repair/resolve and hard.difficulty/difficult)
  word_used: resolve unprompted correct; difficult prompted correct; one misuse (correct=false)
  acceptance_rate = 2/4 = 0.5
  spontaneous: 2 accepts in window; 1 has unprompted correct use → 0.5
  misuse_rate = 1/3

Drills:
  week_old attempt score=3; week_new attempt score=5
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lexicon_fixture import seed_lexicon
from sqlalchemy.orm import Session

from vocab.auth.models import User
from vocab.conversation.models import Conversation, Message, MessageLemmaCount
from vocab.drills.models import Drill, DrillAttempt
from vocab.editor.models import EditorRun, Suggestion
from vocab.events import Event
from vocab.llm.models import LlmCall

ANCHOR = datetime(2026, 11, 10, 12, 0, 0, tzinfo=UTC)
WINDOW_START = ANCHOR - timedelta(days=14)
WEEK_OLD = ANCHOR - timedelta(days=10)
WEEK_NEW = ANCHOR - timedelta(days=3)


def seed_metrics_fixture(session: Session, user: User) -> dict[str, object]:
    """Insert the two-week corpus; return ids useful to tests."""
    seed_lexicon(session)

    conversation = Conversation(user_id=user.id, title="Metrics fixture")
    session.add(conversation)
    session.flush()

    msg_old = Message(
        id="msg-old",
        conversation_id=conversation.id,
        user_id=user.id,
        role="user",
        content="we fix fix hard thing thing thing",
        word_count=10,
        created_at=WEEK_OLD,
    )
    msg_new = Message(
        id="msg-new",
        conversation_id=conversation.id,
        user_id=user.id,
        role="user",
        content="we fix big thing thing xx yy zz",
        word_count=10,
        created_at=WEEK_NEW,
    )
    session.add_all([msg_old, msg_new])
    session.flush()

    counts = [
        ("msg-old", "fix", "fix", 2),
        ("msg-old", "hard", "hard", 1),
        ("msg-old", "thing", "thing", 3),
        ("msg-new", "fix", "fix", 1),
        ("msg-new", "big", "big", 1),
        ("msg-new", "thing", "thing", 2),
    ]
    for message_id, lemma, surface, count in counts:
        session.add(
            MessageLemmaCount(
                message_id=message_id,
                user_id=user.id,
                lemma=lemma,
                surface=surface,
                count=count,
            )
        )

    # Editor plumbing for acceptance filter join.
    call = LlmCall(
        id="llm-editor-1",
        user_id=user.id,
        role="editor",
        model="test-editor",
        prompt_id="editor",
        prompt_version=1,
        input_tokens=1,
        output_tokens=1,
        cost_usd=0.0,
        latency_ms=1,
        status="ok",
        error=None,
        created_at=WEEK_NEW,
    )
    session.add(call)
    session.flush()
    run = EditorRun(
        id="erun-1",
        message_id="msg-new",
        user_id=user.id,
        llm_call_id=call.id,
        output={},
        created_at=WEEK_NEW,
    )
    session.add(run)
    session.flush()

    suggestions = []
    for i in range(4):
        s = Suggestion(
            id=f"sug-{i}",
            editor_run_id=run.id,
            message_id="msg-new",
            user_id=user.id,
            original_text="fix" if i < 2 else "hard",
            span_start=0,
            span_end=3,
            group_id="fix.repair" if i < 2 else "hard.difficulty",
            question=None,
            rank=i,
        )
        session.add(s)
        suggestions.append(s)
    session.flush()

    for i in range(4):
        session.add(
            Event(
                user_id=user.id,
                type="suggestion_shown",
                subject_type="suggestion",
                subject_id=suggestions[i].id,
                payload={"group_id": suggestions[i].group_id},
                created_at=WEEK_NEW,
            )
        )
    session.add(
        Event(
            user_id=user.id,
            type="suggestion_accepted",
            subject_type="suggestion",
            subject_id="sug-0",
            payload={"option_id": "fix.repair/resolve", "word": "resolve"},
            created_at=WEEK_NEW,
        )
    )
    session.add(
        Event(
            user_id=user.id,
            type="suggestion_accepted",
            subject_type="suggestion",
            subject_id="sug-2",
            payload={"option_id": "hard.difficulty/difficult", "word": "difficult"},
            created_at=WEEK_NEW,
        )
    )

    # word_used: unprompted correct for resolve; prompted correct for difficult; one misuse
    session.add(
        Event(
            user_id=user.id,
            type="word_used",
            subject_type="message",
            subject_id="msg-new",
            payload={
                "option_id": "fix.repair/resolve",
                "correct": True,
                "prompted": False,
                "judge_call_id": None,
            },
            created_at=WEEK_NEW,
        )
    )
    session.add(
        Event(
            user_id=user.id,
            type="word_used",
            subject_type="message",
            subject_id="msg-new",
            payload={
                "option_id": "hard.difficulty/difficult",
                "correct": True,
                "prompted": True,
                "judge_call_id": None,
            },
            created_at=WEEK_NEW,
        )
    )
    session.add(
        Event(
            user_id=user.id,
            type="word_used",
            subject_type="message",
            subject_id="msg-old",
            payload={
                "option_id": "fix.repair/patch",
                "correct": False,
                "prompted": False,
                "judge_call_id": None,
            },
            created_at=WEEK_OLD,
        )
    )

    drill_old = Drill(
        id="drill-old",
        user_id=user.id,
        group_id="fix.repair",
        vague_sentence="please fix it",
        intended_option_id="fix.repair/resolve",
        intended_word="resolve",
        created_at=WEEK_OLD,
    )
    drill_new = Drill(
        id="drill-new",
        user_id=user.id,
        group_id="fix.repair",
        vague_sentence="please fix it again",
        intended_option_id="fix.repair/resolve",
        intended_word="resolve",
        created_at=WEEK_NEW,
    )
    session.add_all([drill_old, drill_new])
    session.flush()
    session.add(
        DrillAttempt(
            drill_id="drill-old",
            user_id=user.id,
            answer="resolve it",
            grade={"precision": 3, "meaning": 3, "naturalness": 3},
            score=3,
            created_at=WEEK_OLD,
        )
    )
    session.add(
        DrillAttempt(
            drill_id="drill-new",
            user_id=user.id,
            answer="resolve it well",
            grade={"precision": 5, "meaning": 5, "naturalness": 5},
            score=5,
            created_at=WEEK_NEW,
        )
    )
    session.commit()
    return {
        "window_start": WINDOW_START,
        "window_end": ANCHOR,
        "week_old": WEEK_OLD,
        "week_new": WEEK_NEW,
    }
