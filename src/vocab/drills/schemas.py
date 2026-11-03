"""Structured outputs for drill generation and grading."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class DrillGenOutput(BaseModel):
    vague_sentence: str
    intended_option_id: str
    intended_word: str


class DrillGradeOutput(BaseModel):
    precision: int = Field(ge=1, le=5)
    meaning: int = Field(ge=1, le=5)
    naturalness: int = Field(ge=1, le=5)
    feedback: str
    better_version: str | None = None
    used_option_id: str | None = None

    @model_validator(mode="after")
    def require_better_when_weak(self) -> DrillGradeOutput:
        mean = (self.precision + self.meaning + self.naturalness) / 3
        if mean < 4 and not (self.better_version and self.better_version.strip()):
            raise ValueError("better_version is required when mean score is below 4")
        return self

    @property
    def score(self) -> int:
        return round((self.precision + self.meaning + self.naturalness) / 3)
