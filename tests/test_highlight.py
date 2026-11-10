"""On-spot colour marks for editor suggestions."""

from __future__ import annotations

from vocab.conversation.highlight import highlight_message
from vocab.editor.models import Suggestion


def test_highlight_assigns_distinct_mark_classes() -> None:
    text = "It was a big hard problem."
    suggestions = [
        Suggestion(
            id="s1",
            editor_run_id="r",
            message_id="m",
            user_id="u",
            original_text="big",
            span_start=9,
            span_end=12,
            group_id=None,
            question=None,
            rank=0,
        ),
        Suggestion(
            id="s2",
            editor_run_id="r",
            message_id="m",
            user_id="u",
            original_text="hard",
            span_start=13,
            span_end=17,
            group_id=None,
            question=None,
            rank=1,
        ),
    ]
    html = highlight_message(text, suggestions, keep=["problem"])
    assert 'class="mark-a"' in html
    assert 'class="mark-b"' in html
    assert 'class="mark-keep"' in html
    assert "big" in html and "hard" in html
