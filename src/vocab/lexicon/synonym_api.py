"""Free synonym APIs that seed the editor prompt (never shown raw).

Sources:
- Free Dictionary API (dictionaryapi.dev) for sense-linked synonyms
- Datamuse rel_syn as a second pass

Both soft-fail. The editor model must still pick words that fit the sentence.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DATAMUSE_URL = "https://api.datamuse.com/words"
DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
_DEFAULT_TIMEOUT = 2.5
_MAX_PER_LEMMA = 12
_POS_TAG = {
    "NOUN": "n",
    "VERB": "v",
    "ADJ": "adj",
    "ADV": "adv",
}
_DICT_POS = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
}
# WordNet-style senses that almost never help workplace writing feedback.
_BLOCKED = frozenset(
    {
        "castrate",
        "desex",
        "neuter",
        "spay",
        "impale",
        "doctor",
        "sterilise",
        "sterilize",
        "unsex",
        "rig",
        "jam",
        "hole",
        "muddle",
        "posit",
    }
)


def _pos_tag(pos: str | None) -> str | None:
    if not pos:
        return None
    return _POS_TAG.get(pos.upper())


def _dict_pos(pos: str | None) -> str | None:
    if not pos:
        return None
    return _DICT_POS.get(pos.upper())


def _add_word(words: list[str], seen: set[str], word: str, lemma: str) -> None:
    cleaned = word.strip().lower()
    if not cleaned or cleaned == lemma.lower() or cleaned in seen:
        return
    if cleaned in _BLOCKED:
        return
    if " " in cleaned and len(cleaned.split()) > 3:
        return
    seen.add(cleaned)
    words.append(cleaned)


async def _fetch_dictionary(
    client: httpx.AsyncClient,
    lemma: str,
    pos: str | None,
) -> list[str]:
    want = _dict_pos(pos)
    try:
        response = await client.get(DICTIONARY_URL.format(word=lemma))
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload: list[dict[str, Any]] = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("dictionaryapi failed for %r: %s", lemma, exc)
        return []

    words: list[str] = []
    seen: set[str] = set()
    for entry in payload:
        for meaning in entry.get("meanings") or []:
            speech = str(meaning.get("partOfSpeech") or "").lower()
            if want and speech and speech != want:
                continue
            for syn in meaning.get("synonyms") or []:
                _add_word(words, seen, str(syn), lemma)
                if len(words) >= _MAX_PER_LEMMA:
                    return words
            for definition in meaning.get("definitions") or []:
                for syn in definition.get("synonyms") or []:
                    _add_word(words, seen, str(syn), lemma)
                    if len(words) >= _MAX_PER_LEMMA:
                        return words
    return words


async def _fetch_datamuse(
    client: httpx.AsyncClient,
    lemma: str,
    pos: str | None,
) -> list[str]:
    params: dict[str, str | int] = {
        "rel_syn": lemma,
        "max": _MAX_PER_LEMMA,
        "md": "p",
    }
    want_pos = _pos_tag(pos)
    try:
        response = await client.get(DATAMUSE_URL, params=params)
        response.raise_for_status()
        rows: list[dict[str, Any]] = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("datamuse failed for %r: %s", lemma, exc)
        return []

    # Prefer higher Datamuse scores when present.
    rows = sorted(rows, key=lambda row: int(row.get("score") or 0), reverse=True)
    words: list[str] = []
    seen: set[str] = set()
    for row in rows:
        tags = {str(t) for t in (row.get("tags") or [])}
        if want_pos and tags and want_pos not in tags:
            continue
        _add_word(words, seen, str(row.get("word") or ""), lemma)
        if len(words) >= _MAX_PER_LEMMA:
            break
    return words


async def _fetch_lemma(
    client: httpx.AsyncClient,
    lemma: str,
    pos: str | None,
) -> list[str]:
    dict_words, dm_words = await asyncio.gather(
        _fetch_dictionary(client, lemma, pos),
        _fetch_datamuse(client, lemma, pos),
    )
    merged: list[str] = []
    seen: set[str] = set()
    for word in dict_words + dm_words:
        if word in seen:
            continue
        seen.add(word)
        merged.append(word)
        if len(merged) >= _MAX_PER_LEMMA:
            break
    return merged


async def synonym_hints(
    lemmas: list[tuple[str, str | None]],
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, list[str]]:
    """Map lemma -> synonym strings. Soft-fails to {} when the network is down."""
    unique: dict[str, str | None] = {}
    for lemma, pos in lemmas:
        key = lemma.strip().lower()
        if not key or key in unique:
            continue
        unique[key] = pos

    if not unique:
        return {}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            pairs = list(unique.items())
            results = await asyncio.gather(
                *[_fetch_lemma(client, lemma, pos) for lemma, pos in pairs]
            )
    except httpx.HTTPError as exc:
        logger.warning("synonym API client failed: %s", exc)
        return {}

    return {lemma: words for (lemma, _), words in zip(pairs, results, strict=True) if words}
