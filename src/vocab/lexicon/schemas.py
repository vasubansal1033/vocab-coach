"""Pydantic shapes for seed YAML and group_gen LLM output."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OptionSeed(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    word: str
    distinction: str
    example: str
    # Named speech_register in code; YAML/JSON still use "register".
    speech_register: Literal["neutral", "formal", "technical"] = Field(
        default="neutral", alias="register"
    )


class GroupSeed(BaseModel):
    id: str
    pos: str
    sense_gloss: str
    options: list[OptionSeed] = Field(min_length=1)


class LemmaSeedFile(BaseModel):
    head_lemma: str
    groups: list[GroupSeed] = Field(min_length=1)


class GroupGenOutput(BaseModel):
    """Structured reply from the group_gen role."""

    head_lemma: str
    groups: list[GroupSeed] = Field(min_length=1)
