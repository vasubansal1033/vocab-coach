"""Editor LLM output contract."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EditorOption(BaseModel):
    word: str
    meaning: str = Field(description="What this word says that the original does not")
    option_id: str | None = Field(
        default=None, description="ID from the supplied groups, or null for a new word"
    )


class EditorSuggestion(BaseModel):
    original: str = Field(description="Exact substring of the user's message")
    group_id: str | None = None
    options: list[EditorOption] = Field(min_length=1, max_length=3)
    question: str | None = Field(
        default=None,
        description="Ask when the right word depends on facts you do not know",
    )
    why: str = Field(description="One sentence on what is vague about the original")


class EditorOutput(BaseModel):
    overview: str = Field(
        default="",
        description="One or two sentences on how the whole message reads and its main vagueness",
    )
    suggestions: list[EditorSuggestion] = Field(max_length=3)
    keep: list[str] = Field(
        description="Words that looked like candidates but are already the right word"
    )
