"""Structured schemas for choose-the-word exercises."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Fit = Literal["fits", "partly", "wrong"]


class ChoiceCandidate(BaseModel):
    option_id: str
    fit: Fit
    reason: str
    best: bool


class ChoiceGenOutput(BaseModel):
    """LLM output for choice_gen; validated before persistence."""

    situation: str
    sentence: str
    candidates: list[ChoiceCandidate] = Field(min_length=4, max_length=6)

    @model_validator(mode="after")
    def require_blank_and_one_best(self) -> ChoiceGenOutput:
        if self.sentence.count("___") != 1:
            raise ValueError("sentence must contain exactly one ___ blank")
        bests = [c for c in self.candidates if c.best]
        if len(bests) != 1:
            raise ValueError("exactly one candidate must have best=true")
        return self


class ChoicePromptCandidate(BaseModel):
    option_id: str
    word: str


class ChoicePrompt(BaseModel):
    """What the browser may see before an attempt."""

    situation: str
    sentence: str
    candidates: list[ChoicePromptCandidate]


class ChoiceAnswerCandidate(BaseModel):
    option_id: str
    fit: Fit
    reason: str
    best: bool


class ChoiceAnswer(BaseModel):
    """Stored answers; never sent before the attempt is submitted."""

    candidates: list[ChoiceAnswerCandidate]
    best_option_id: str


class ChoiceResponse(BaseModel):
    """User's pick: best option plus every candidate they marked as fitting."""

    best_option_id: str
    marked_option_ids: list[str] = Field(default_factory=list)


class ChoiceFeedbackCandidate(BaseModel):
    option_id: str
    fit: Fit
    reason: str
    best: bool
    user_marked: bool


class ChoiceFeedback(BaseModel):
    best_option_id: str
    user_best_option_id: str
    candidates: list[ChoiceFeedbackCandidate]
