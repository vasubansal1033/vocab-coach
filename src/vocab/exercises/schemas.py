"""Structured schemas for choose-the-word, compare, and idiom exercises."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Fit = Literal["fits", "partly", "wrong"]
CompareItemType = Literal["compare_pair", "compare_misuse", "compare_order"]
IdiomItemType = Literal[
    "idiom_recognise", "idiom_meaning", "idiom_situation", "idiom_write"
]
IdiomLlmItemType = Literal["idiom_recognise", "idiom_meaning", "idiom_situation"]


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


# --- Compare: pair ---


class ComparePairSentenceGen(BaseModel):
    text: str
    fits_option_id: str

    @model_validator(mode="after")
    def require_one_blank(self) -> ComparePairSentenceGen:
        if self.text.count("___") != 1:
            raise ValueError("each pair sentence must contain exactly one ___ blank")
        return self


class ComparePairGenOutput(BaseModel):
    """LLM output for compare_pair items."""

    sentences: list[ComparePairSentenceGen] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def distinct_fits(self) -> ComparePairGenOutput:
        ids = [s.fits_option_id for s in self.sentences]
        if len(set(ids)) != 2:
            raise ValueError("pair sentences must fit two different option_ids")
        return self


class ComparePairPrompt(BaseModel):
    sentences: list[str]
    options: list[ChoicePromptCandidate]


class ComparePairAnswer(BaseModel):
    fits_option_ids: list[str] = Field(min_length=2, max_length=2)


class ComparePairResponse(BaseModel):
    fits_option_ids: list[str] = Field(min_length=2, max_length=2)


class ComparePairFeedback(BaseModel):
    fits_option_ids: list[str]
    user_fits_option_ids: list[str]


# --- Compare: misuse ---


class CompareMisuseGenOutput(BaseModel):
    """LLM output for compare_misuse items."""

    sentence: str
    misused_option_id: str
    replacement_option_id: str
    reason: str

    @model_validator(mode="after")
    def distinct_ids(self) -> CompareMisuseGenOutput:
        if self.misused_option_id == self.replacement_option_id:
            raise ValueError("misused and replacement option_ids must differ")
        if not self.sentence.strip():
            raise ValueError("misuse sentence must not be empty")
        if not self.reason.strip():
            raise ValueError("misuse reason must not be empty")
        return self


class CompareMisusePrompt(BaseModel):
    sentence: str
    options: list[ChoicePromptCandidate]


class CompareMisuseAnswer(BaseModel):
    misused_option_id: str
    replacement_option_id: str
    reason: str


class CompareMisuseResponse(BaseModel):
    misused_option_id: str
    replacement_option_id: str


class CompareMisuseFeedback(BaseModel):
    misused_option_id: str
    replacement_option_id: str
    user_misused_option_id: str
    user_replacement_option_id: str
    reason: str


# --- Compare: order ---


class CompareOrderPrompt(BaseModel):
    options: list[ChoicePromptCandidate]


class CompareOrderAnswer(BaseModel):
    ordered_option_ids: list[str] = Field(min_length=2)


class CompareOrderResponse(BaseModel):
    ordered_option_ids: list[str] = Field(min_length=2)


class CompareOrderFeedback(BaseModel):
    ordered_option_ids: list[str]
    user_ordered_option_ids: list[str]


# --- Idioms: recognise / meaning / situation (LLM) and write (usage_judge) ---


class IdiomSelectChoice(BaseModel):
    id: str
    label: str


class IdiomRecogniseGenOutput(BaseModel):
    """LLM output: paragraph that uses one idiom; user picks which."""

    paragraph: str
    option_id: str
    choices: list[IdiomSelectChoice] = Field(min_length=3, max_length=4)

    @model_validator(mode="after")
    def one_correct_option(self) -> IdiomRecogniseGenOutput:
        if not self.paragraph.strip():
            raise ValueError("paragraph must not be empty")
        ids = [c.id for c in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError("choice ids must be unique")
        if self.option_id not in ids:
            raise ValueError("option_id must appear in choices")
        return self


class IdiomMeaningGenOutput(BaseModel):
    """LLM output: pick the correct meaning for one idiom."""

    option_id: str
    choices: list[IdiomSelectChoice] = Field(min_length=3, max_length=4)
    correct_id: str

    @model_validator(mode="after")
    def one_correct(self) -> IdiomMeaningGenOutput:
        ids = [c.id for c in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError("choice ids must be unique")
        if self.correct_id not in ids:
            raise ValueError("correct_id must appear in choices")
        return self


class IdiomSituationGenOutput(BaseModel):
    """LLM output: pick the situation where the idiom fits."""

    option_id: str
    choices: list[IdiomSelectChoice] = Field(min_length=3, max_length=4)
    correct_id: str

    @model_validator(mode="after")
    def one_correct(self) -> IdiomSituationGenOutput:
        ids = [c.id for c in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError("choice ids must be unique")
        if self.correct_id not in ids:
            raise ValueError("correct_id must appear in choices")
        return self


class IdiomSelectPrompt(BaseModel):
    """Shared prompt shape for recognise / meaning / situation."""

    stem: str
    word: str | None = None
    choices: list[IdiomSelectChoice]


class IdiomSelectAnswer(BaseModel):
    correct_id: str
    option_id: str


class IdiomSelectResponse(BaseModel):
    selected_id: str


class IdiomSelectFeedback(BaseModel):
    correct_id: str
    selected_id: str
    option_id: str


class IdiomWritePrompt(BaseModel):
    option_id: str
    word: str
    meaning: str
    avoid_when: str


class IdiomWriteAnswer(BaseModel):
    option_id: str
    word: str
    meaning: str


class IdiomWriteResponse(BaseModel):
    sentence: str = Field(min_length=1)


class IdiomWriteFeedback(BaseModel):
    correct: bool
    explanation: str
    option_id: str
    word: str
