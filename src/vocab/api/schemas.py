"""Pydantic request/response models for the JSON API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class UserOut(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    feedback_expectations: str | None = None
    flow_mode: bool = False
    allow_idioms: bool = False
    created_at: str | None = None
    messages: list[MessageOut] | None = None


class ConversationListOut(BaseModel):
    conversations: list[ConversationOut]


class ConversationCreateIn(BaseModel):
    """Name is required; feedback_expectations steers the editor when set."""

    name: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    feedback_expectations: str | None = Field(default=None, max_length=4000)
    flow_mode: bool = False
    allow_idioms: bool = False

    @model_validator(mode="after")
    def require_nonblank_name(self) -> ConversationCreateIn:
        if not self.resolved_name():
            raise ValueError("name is required")
        brief = self.feedback_expectations
        if brief is not None:
            self.feedback_expectations = brief.strip() or None
        return self

    def resolved_name(self) -> str:
        return (self.name or self.topic or "").strip()


class MessageIn(BaseModel):
    content: str = Field(min_length=1)


class AcceptIn(BaseModel):
    option_id: str


class RetryIn(BaseModel):
    option_id: str


class RetryOut(BaseModel):
    text: str


class RecapWordOut(BaseModel):
    word: str
    option_id: str | None = None
    source: str


class RecapCrutchOut(BaseModel):
    lemma: str
    count: int


class RecapOut(BaseModel):
    words_to_keep: list[RecapWordOut]
    crutch_words: list[RecapCrutchOut]
    rewrite_sentence: str | None = None


class SuggestionOptionOut(BaseModel):
    id: str
    word: str
    meaning: str


class SuggestionOut(BaseModel):
    id: str
    original_text: str
    span_start: int
    span_end: int
    question: str | None = None
    why: str | None = None
    options: list[SuggestionOptionOut]


class FeedbackOut(BaseModel):
    failed: bool
    content: str
    overview: str | None = None
    highlighted_html: str = ""
    keep: list[str] = Field(default_factory=list)
    suggestions: list[SuggestionOut] = Field(default_factory=list)


class SuggestionActionOut(BaseModel):
    dismissed: bool
    accepted_word: str | None = None
    original_text: str


class MetricWeekOut(BaseModel):
    label: str
    rate: float | None = None


class DrillWeekOut(BaseModel):
    label: str
    score: float | None = None


class OveruseGroupOut(BaseModel):
    id: str
    sense_gloss: str


class OveruseRowOut(BaseModel):
    word: str
    uses: int
    lift: float
    groups: list[OveruseGroupOut]


class DashboardOut(BaseModel):
    window_start: str
    window_end: str
    crutch_rate: float | None
    weekly: list[MetricWeekOut]
    overuse: list[OveruseRowOut]
    acceptance: float | None
    spontaneous: float | None
    misuse: float | None
    drill_weeks: list[DrillWeekOut]
    mtld: float | None


class LemmaOptionOut(BaseModel):
    option_id: str
    word: str
    uses: int
    correct_uses: int


class LemmaDetailOut(BaseModel):
    lemma: str
    weekly: list[MetricWeekOut]
    options: list[LemmaOptionOut]


class ReviewOptionOut(BaseModel):
    id: str
    word: str
    distinction: str
    example: str
    cloze: str


class ReviewDueOut(BaseModel):
    option: ReviewOptionOut | None


class ReviewIn(BaseModel):
    rating: str
    answer: str = ""


class StatusOut(BaseModel):
    status: str


class DrillOut(BaseModel):
    id: str
    vague_sentence: str
    intended_word: str
    context: str | None = None
    intended_distinction: str | None = None


class DrillAnswerIn(BaseModel):
    answer: str = Field(min_length=1)
    hints_used: int = Field(default=0, ge=0, le=3)


class DrillAttemptOut(BaseModel):
    id: str
    answer: str
    score: float | None = None
    grade: dict[str, Any] | None = None
    hints_used: int = 0


class DrillHintOut(BaseModel):
    level: int
    text: str


class DrillDisputeIn(BaseModel):
    note: str | None = None


class DrillSummaryOut(BaseModel):
    mean_score: float
    words_practised: list[str]
    total_hints_used: int


class AccountLimitsOut(BaseModel):
    llm_calls_24h: int
    llm_call_limit_per_day: int
    llm_cost_usd_24h: float
    llm_cost_limit_usd_per_day: float


class AccountOut(BaseModel):
    user: UserOut
    limits: AccountLimitsOut
    privacy_note: str
