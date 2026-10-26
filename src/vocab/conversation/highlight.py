"""Mark suggestion spans in message HTML using stored character offsets."""

from __future__ import annotations

import html

from vocab.editor.models import Suggestion


def highlight_message(text: str, suggestions: list[Suggestion]) -> str:
    """Escape text and wrap each suggestion span in <mark>."""
    if not suggestions:
        return html.escape(text)
    spans = sorted(
        ((s.span_start, s.span_end, s.id) for s in suggestions),
        key=lambda item: item[0],
    )
    parts: list[str] = []
    cursor = 0
    for start, end, sid in spans:
        if start < cursor or end > len(text) or start >= end:
            continue
        parts.append(html.escape(text[cursor:start]))
        parts.append(f'<mark id="span-{html.escape(sid)}">')
        parts.append(html.escape(text[start:end]))
        parts.append("</mark>")
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)
