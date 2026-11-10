"""Mark suggestion spans in message HTML using stored character offsets."""

from __future__ import annotations

import html

from vocab.editor.models import Suggestion

# Distinct colours for concurrent vague spots in one message.
_MARK_CLASSES = ("mark-a", "mark-b", "mark-c")


def highlight_message(
    text: str,
    suggestions: list[Suggestion],
    *,
    keep: list[str] | None = None,
) -> str:
    """Escape text; wrap suggestion spans in coloured marks; optional keep marks."""
    marks: list[tuple[int, int, str, str]] = []
    for index, suggestion in enumerate(
        sorted(suggestions, key=lambda s: (s.span_start, s.span_end))
    ):
        cls = _MARK_CLASSES[index % len(_MARK_CLASSES)]
        marks.append((suggestion.span_start, suggestion.span_end, cls, suggestion.id))

    if keep:
        for word in keep:
            start = text.find(word)
            if start < 0:
                continue
            end = start + len(word)
            # Skip if this range overlaps a suggestion mark.
            if any(not (end <= m0 or start >= m1) for m0, m1, _c, _i in marks):
                continue
            marks.append((start, end, "mark-keep", f"keep-{start}"))

    marks.sort(key=lambda item: item[0])
    parts: list[str] = []
    cursor = 0
    for start, end, cls, sid in marks:
        if start < cursor or end > len(text) or start >= end:
            continue
        parts.append(html.escape(text[cursor:start]))
        safe_id = html.escape(sid)
        parts.append(f'<mark class="{cls}" data-span="{safe_id}" id="span-{safe_id}">')
        parts.append(html.escape(text[start:end]))
        parts.append("</mark>")
        cursor = end
    parts.append(html.escape(text[cursor:]))
    return "".join(parts)
