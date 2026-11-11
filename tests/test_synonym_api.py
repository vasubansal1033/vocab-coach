"""Synonym API helper: merge sources, POS filter, soft failure."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from vocab.lexicon.synonym_api import synonym_hints


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://example.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> object:
        return self._payload


@pytest.mark.asyncio
async def test_synonym_hints_prefers_dictionary_then_datamuse() -> None:
    dict_payload = [
        {
            "meanings": [
                {
                    "partOfSpeech": "verb",
                    "synonyms": ["rectify", "patch"],
                    "definitions": [{"synonyms": ["mend"]}],
                }
            ]
        }
    ]
    dm_payload = [
        {"word": "secure", "score": 100, "tags": ["v"]},
        {"word": "fixture", "score": 50, "tags": ["n"]},
        {"word": "fix", "score": 1, "tags": ["v"]},
    ]

    async def fake_get(url: str, params: dict[str, object] | None = None) -> _FakeResponse:
        _ = params
        if "dictionaryapi.dev" in str(url):
            return _FakeResponse(dict_payload)
        return _FakeResponse(dm_payload)

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=fake_get)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    with patch("vocab.lexicon.synonym_api.httpx.AsyncClient", return_value=fake_client):
        hints = await synonym_hints([("fix", "VERB")])

    assert hints["fix"][:3] == ["rectify", "patch", "mend"]
    assert "secure" in hints["fix"]
    assert "fixture" not in hints["fix"]


@pytest.mark.asyncio
async def test_synonym_hints_soft_fails() -> None:
    fake_client = AsyncMock()
    fake_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)

    with patch("vocab.lexicon.synonym_api.httpx.AsyncClient", return_value=fake_client):
        hints = await synonym_hints([("good", "ADJ")])

    assert hints == {}
