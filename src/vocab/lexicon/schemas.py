"""Pydantic shapes for seed YAML and lexicon drafting LLM output."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

GroupKind = Literal["precision", "confusable", "idiom"]


class ConfusableDetails(BaseModel):
    """Extra fields on a confusable-set option."""

    collocations: list[str] = Field(default_factory=list)
    connotation: Literal["positive", "neutral", "negative"] = "neutral"
    strength: int | None = None


class IdiomDetails(BaseModel):
    """Extra fields on an idiom option."""

    meaning: str
    tier: Literal["everyday", "literary"] = "everyday"
    region: Literal["common", "uk", "us"] = "common"
    variants: list[str] = Field(default_factory=list)
    misuse_example: str
    avoid_when: str
    origin: str | None = None

    @model_validator(mode="after")
    def literary_needs_origin(self) -> Self:
        """Literary idioms need the story that helps the user remember them."""
        if self.tier == "literary" and not (self.origin and self.origin.strip()):
            raise ValueError("literary idioms require origin")
        return self


def validate_details(kind: GroupKind, details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Parse option details for the group's kind; reject mismatches."""
    if kind == "precision":
        if details:
            raise ValueError("precision options must not carry details")
        return None
    if kind == "confusable":
        return ConfusableDetails.model_validate(details or {}).model_dump()
    if kind == "idiom":
        if details is None:
            raise ValueError("idiom options require details")
        return IdiomDetails.model_validate(details).model_dump()
    raise ValueError(f"unknown kind: {kind}")


class OptionSeed(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    word: str
    distinction: str
    example: str
    # Named speech_register in code; YAML/JSON still use "register".
    speech_register: Literal["neutral", "formal", "technical"] = Field(
        default="neutral", alias="register"
    )
    details: dict[str, Any] | None = None


class GroupSeed(BaseModel):
    id: str
    pos: str
    sense_gloss: str
    options: list[OptionSeed] = Field(min_length=1)


class LemmaSeedFile(BaseModel):
    """One YAML seed file; missing kind means precision."""

    kind: GroupKind = "precision"
    head_lemma: str | None = None
    groups: list[GroupSeed] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_kind_shape(self) -> Self:
        """Enforce head_lemma and option details rules per kind."""
        if self.kind in ("precision", "idiom"):
            if not self.head_lemma or not self.head_lemma.strip():
                raise ValueError(f"{self.kind} seeds require head_lemma")
        elif self.kind == "confusable":
            if self.head_lemma is not None and str(self.head_lemma).strip() != "":
                raise ValueError("confusable seeds must leave head_lemma empty")
            self.head_lemma = None
        for group in self.groups:
            for opt in group.options:
                opt.details = validate_details(self.kind, opt.details)
        return self


class GroupGenOutput(BaseModel):
    """Structured reply from the group_gen role."""

    head_lemma: str
    groups: list[GroupSeed] = Field(min_length=1)


class ConfusableGenOutput(BaseModel):
    """Structured reply from the confusable_gen role."""

    kind: Literal["confusable"] = "confusable"
    head_lemma: None = None
    groups: list[GroupSeed] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_details(self) -> Self:
        for group in self.groups:
            for opt in group.options:
                opt.details = validate_details("confusable", opt.details)
        return self


class IdiomGenOutput(BaseModel):
    """Structured reply from the idiom_gen role."""

    kind: Literal["idiom"] = "idiom"
    head_lemma: str
    groups: list[GroupSeed] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_details(self) -> Self:
        if not self.head_lemma.strip():
            raise ValueError("idiom drafts require head_lemma")
        for group in self.groups:
            for opt in group.options:
                opt.details = validate_details("idiom", opt.details)
        return self
