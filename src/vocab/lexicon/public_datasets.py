"""Fetch public lexicon datasets and map them into LemmaSeedFile shapes.

Sources (fetched at import time, not shipped in-repo):

- Lexkite commonly-confused words (CC BY 4.0)
- ABC Thesaurus dump + vs-notes (CC BY-SA 4.0)

Attribution must stay with any redistributed derivative.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

import httpx
import yaml

from vocab.lexicon.schemas import LemmaSeedFile

SourceName = Literal["lexkite", "abc_precision", "abc_confusable"]

LEXKITE_JSON_URL = (
    "https://huggingface.co/datasets/mrquyenbkpro/confused-english-words/"
    "resolve/main/confused-words.json"
)
ABC_JSONL_URL = "https://abcthesaurus.com/data/abcthesaurus-en.jsonl.gz"
ABC_VS_NOTES_URL = "https://abcthesaurus.com/data/abcthesaurus-vs-notes.csv.gz"

POS_MAP = {
    "v": "VERB",
    "verb": "VERB",
    "n": "NOUN",
    "noun": "NOUN",
    "adj": "ADJ",
    "adv": "ADV",
}

REGISTER_MAP = {
    "neutral": "neutral",
    "formal": "formal",
    "technical": "technical",
    "informal": "neutral",
    "slang": "neutral",
    "dated": "neutral",
    "literary": "neutral",
}

_CRUTCH_PATH = Path(__file__).resolve().parents[3] / "data" / "crutch_words.yaml"
_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Extra vague heads beyond the crutch list; ABC supplies sense-aware synonyms.
EXTRA_PRECISION_LEMMAS = frozenset(
    {
        "small",
        "little",
        "pretty",
        "quite",
        "somehow",
        "put",
        "take",
        "give",
        "keep",
        "start",
        "stop",
        "change",
        "move",
        "seem",
        "feel",
        "know",
        "try",
        "ask",
        "tell",
        "work",
        "find",
        "leave",
        "call",
        "set",
        "turn",
        "bring",
        "happen",
        "allow",
        "include",
        "create",
        "provide",
        "require",
        "consider",
        "develop",
        "increase",
        "reduce",
        "improve",
        "support",
        "manage",
        "handle",
        "address",
        "cover",
        "check",
        "ensure",
        "avoid",
        "prevent",
        "cause",
        "lead",
        "result",
        "impact",
        "affect",
        "focus",
        "rely",
        "depend",
        "involve",
        "contain",
        "mean",
        "deal",
        "base",
    }
)


def _slug(text: str, *, max_len: int = 48) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug or "x")[:max_len]


def _map_register(raw: str | None) -> str:
    return REGISTER_MAP.get((raw or "neutral").lower(), "neutral")


def _map_pos(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    return POS_MAP.get(key, "NOUN")


def _intensity_phrase(lemma: str, intensity: int | None) -> str:
    if intensity is None or intensity == 0:
        return f"near synonym of «{lemma}»"
    if intensity > 0:
        return f"stronger than «{lemma}»"
    return f"milder than «{lemma}»"


def _cache_dir() -> Path:
    root = Path(tempfile.gettempdir()) / "vocab-coach-public-lexicon"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _download(url: str, *, filename: str, timeout: float = 120.0) -> Path:
    """Cache remote bytes so repeated admin imports stay cheap."""
    path = _cache_dir() / filename
    if path.exists() and path.stat().st_size > 0:
        return path
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        path.write_bytes(response.content)
    return path


def _crutch_lemmas() -> set[str]:
    raw = yaml.safe_load(_CRUTCH_PATH.read_text(encoding="utf-8"))
    return {str(row["lemma"]).lower() for row in raw}


def _precision_target_lemmas() -> set[str]:
    return _crutch_lemmas() | {lemma.lower() for lemma in EXTRA_PRECISION_LEMMAS}


def lexkite_to_items(payload: dict[str, Any]) -> list[LemmaSeedFile]:
    """Map Lexkite confused-word groups into confusable lexicon items."""
    items: list[LemmaSeedFile] = []
    for group in payload.get("groups") or []:
        words = group.get("words") or []
        if len(words) < 2:
            continue
        group_id = f"confusable.lexkite.{_slug(str(group.get('id') or words[0]['w']))}"
        tip = str(group.get("tip") or "").strip()
        sense = tip or " / ".join(
            f"{w.get('w')}: {w.get('def')}" for w in words if w.get("w") and w.get("def")
        )
        options = []
        for word in words:
            surface = str(word.get("w") or "").strip()
            if not surface:
                continue
            definition = str(word.get("def") or tip or surface).strip()
            example = str(word.get("ex") or "").strip()
            if not example:
                example = f"Use «{surface}» when you mean: {definition}."
            options.append(
                {
                    "word": surface,
                    "distinction": definition,
                    "example": example,
                    "register": "neutral",
                    "details": {
                        "collocations": [],
                        "connotation": "neutral",
                    },
                }
            )
        if len(options) < 2:
            continue
        items.append(
            LemmaSeedFile.model_validate(
                {
                    "kind": "confusable",
                    "head_lemma": None,
                    "groups": [
                        {
                            "id": group_id,
                            "pos": _map_pos(words[0].get("pos")),
                            "sense_gloss": sense[:300],
                            "options": options,
                        }
                    ],
                }
            )
        )
    return items


def abc_precision_to_items(
    rows: list[dict[str, Any]],
    *,
    lemmas: set[str] | None = None,
    max_options: int = 8,
) -> list[LemmaSeedFile]:
    """Build precision groups from ABC Thesaurus senses for target lemmas."""
    targets = lemmas or _precision_target_lemmas()
    items: list[LemmaSeedFile] = []
    used_ids: set[str] = set()
    for row in rows:
        lemma = str(row.get("word") or "").strip().lower()
        if lemma not in targets:
            continue
        for index, sense in enumerate(row.get("senses") or []):
            gloss = str(sense.get("gloss") or "").strip()
            if not gloss:
                continue
            pos = _map_pos(sense.get("pos"))
            syns = list(sense.get("synonyms") or []) + list(sense.get("near_synonyms") or [])
            options: list[dict[str, Any]] = []
            seen: set[str] = set()
            for syn in syns:
                word = str(syn.get("word") or "").strip()
                key = word.lower()
                if not word or key == lemma or key in seen:
                    continue
                seen.add(key)
                intensity = syn.get("intensity")
                try:
                    intensity_i = int(intensity) if intensity is not None else 0
                except (TypeError, ValueError):
                    intensity_i = 0
                distinction = f"{_intensity_phrase(lemma, intensity_i)} in the sense «{gloss}»."
                example = f"Instead of vague «{lemma}», write «{word}» when you mean: {gloss}."
                options.append(
                    {
                        "word": word,
                        "distinction": distinction[:400],
                        "example": example[:400],
                        "register": _map_register(syn.get("register")),
                    }
                )
                if len(options) >= max_options:
                    break
            if len(options) < 2:
                continue
            sense_slug = _slug(gloss, max_len=40)
            group_id = f"{lemma}.abc.{sense_slug}"
            if group_id in used_ids:
                group_id = f"{group_id}-{index}"
            used_ids.add(group_id)
            items.append(
                LemmaSeedFile.model_validate(
                    {
                        "kind": "precision",
                        "head_lemma": lemma,
                        "groups": [
                            {
                                "id": group_id,
                                "pos": pos,
                                "sense_gloss": gloss[:300],
                                "options": options,
                            }
                        ],
                    }
                )
            )
    return items


def abc_vs_notes_to_items(
    rows: list[dict[str, str]],
    *,
    limit: int | None = None,
) -> list[LemmaSeedFile]:
    """Map ABC editorial vs-notes into confusable sets."""
    items: list[LemmaSeedFile] = []
    for row in rows:
        if limit is not None and len(items) >= limit:
            break
        slug = str(row.get("pair_slug") or "").strip()
        word_a = str(row.get("word_a") or "").replace("-", " ").strip()
        word_b = str(row.get("word_b") or "").replace("-", " ").strip()
        note = str(row.get("note") or "").strip()
        if not slug or not word_a or not word_b or not note or word_a.lower() == word_b.lower():
            continue
        # Skip multiword heads that look like phrases with odd hyphens already normalized.
        if len(word_a.split()) > 3 or len(word_b.split()) > 3:
            continue
        group_id = f"confusable.abc.{_slug(slug)}"
        items.append(
            LemmaSeedFile.model_validate(
                {
                    "kind": "confusable",
                    "head_lemma": None,
                    "groups": [
                        {
                            "id": group_id,
                            "pos": "ADJ",
                            "sense_gloss": note[:300],
                            "options": [
                                {
                                    "word": word_a,
                                    "distinction": note[:400],
                                    "example": (f"Prefer «{word_a}» over «{word_b}» when: {note}")[
                                        :400
                                    ],
                                    "register": "neutral",
                                    "details": {
                                        "collocations": [],
                                        "connotation": "neutral",
                                    },
                                },
                                {
                                    "word": word_b,
                                    "distinction": note[:400],
                                    "example": (f"Prefer «{word_b}» over «{word_a}» when: {note}")[
                                        :400
                                    ],
                                    "register": "neutral",
                                    "details": {
                                        "collocations": [],
                                        "connotation": "neutral",
                                    },
                                },
                            ],
                        }
                    ],
                }
            )
        )
    return items


def load_lexkite_items(*, client_fetch: bool = True) -> list[LemmaSeedFile]:
    if not client_fetch:
        raise ValueError("lexkite requires fetch or fixture bytes")
    path = _download(LEXKITE_JSON_URL, filename="confused-words.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return lexkite_to_items(payload)


def load_abc_jsonl_rows() -> list[dict[str, Any]]:
    path = _download(ABC_JSONL_URL, filename="abcthesaurus-en.jsonl.gz")
    raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_abc_vs_note_rows() -> list[dict[str, str]]:
    path = _download(ABC_VS_NOTES_URL, filename="abcthesaurus-vs-notes.csv.gz")
    raw = gzip.decompress(path.read_bytes()).decode("utf-8")
    reader = csv.DictReader(io.StringIO(raw))
    return [dict(row) for row in reader]


def build_public_items(
    sources: list[SourceName] | None = None,
    *,
    abc_confusable_limit: int | None = None,
) -> list[LemmaSeedFile]:
    """Download selected public sources and return validated seed items."""
    chosen = sources or ["lexkite", "abc_precision", "abc_confusable"]
    items: list[LemmaSeedFile] = []
    abc_rows: list[dict[str, Any]] | None = None

    if "lexkite" in chosen:
        items.extend(load_lexkite_items())
    if "abc_precision" in chosen:
        abc_rows = load_abc_jsonl_rows()
        items.extend(abc_precision_to_items(abc_rows))
    if "abc_confusable" in chosen:
        items.extend(
            abc_vs_notes_to_items(
                load_abc_vs_note_rows(),
                limit=abc_confusable_limit,
            )
        )
    return items


def attribution_lines() -> list[str]:
    return [
        "Lexkite Editorial Team — Commonly confused English words (CC BY 4.0) "
        "https://lexkite.com/en/research/confused-words/",
        "ABC Thesaurus — thesaurus dump and vs-notes (CC BY-SA 4.0) https://abcthesaurus.com/data/",
    ]
