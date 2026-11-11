"""QA user journey: exercise /api the way the SPA does, as a signed-in learner."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lexicon_fixture import seed_lexicon
from sqlalchemy.orm import Session

from vocab.auth.deps import current_user
from vocab.auth.models import User
from vocab.config import Settings
from vocab.db import get_session
from vocab.llm.client import use_fake
from vocab.llm.fake import FakeLLM
from vocab.main import create_app
from vocab.practice.srs import ensure_card

REPORT_PATH = Path(__file__).resolve().parents[2] / "evals" / "qa" / "latest-report.json"

EDITOR_FIXTURE = json.dumps(
    {
        "overview": "Several vague spots; tighten the nouns and verbs.",
        "suggestions": [
            {
                "original": "big",
                "group_id": "big.scale",
                "options": [
                    {
                        "word": "substantial",
                        "meaning": "large in amount or importance",
                        "option_id": None,
                    }
                ],
                "question": None,
                "why": "big is vague about scale",
            },
            {
                "original": "hard",
                "group_id": "hard.difficulty",
                "options": [
                    {
                        "word": "difficult",
                        "meaning": "not easy to do",
                        "option_id": None,
                    }
                ],
                "question": None,
                "why": "hard is vague about difficulty",
            },
        ],
        "keep": ["problem"],
    }
)


@pytest.fixture(autouse=True)
def _clear_fake() -> None:
    use_fake(None)
    yield
    use_fake(None)


def _qa_client(session: Session, user: User) -> TestClient:
    """App with FakeLLM-ready role models (empty models break model_for)."""
    settings = Settings(
        _env_file=None,
        session_secret="test-session-secret",
        llm_partner_model="fake-partner",
        llm_editor_model="fake-editor",
        llm_usage_judge_model="fake-judge",
        llm_drill_gen_model="fake-drill-gen",
        llm_drill_grade_model="fake-drill-grade",
        llm_partner_prompt_version=1,
        llm_editor_prompt_version=2,
        llm_usage_judge_prompt_version=1,
        llm_drill_gen_prompt_version=1,
        llm_drill_grade_prompt_version=1,
    )
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[current_user] = lambda: user
    return TestClient(app, follow_redirects=False)


def _write_report(
    *,
    status: str,
    checks: list[dict[str, object]],
    bugs: list[dict[str, object]],
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "status": status,
                "ran_at": datetime.now(UTC).isoformat(),
                "runner": "qa-user-journey",
                "checks": checks,
                "bugs": bugs,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_qa_signed_in_user_journey(
    session: Session,
    make_user: Callable[..., User],
) -> None:
    """Walk the SPA API surface as one user; write evals/qa/latest-report.json."""
    seed_lexicon(session)
    user = make_user("QA Learner")
    client = _qa_client(session, user)
    headers = {"accept": "application/json"}
    checks: list[dict[str, object]] = []
    bugs: list[dict[str, object]] = []

    def check(check_id: str, ok: bool, detail: str, *, severity: str = "major") -> None:
        checks.append({"id": check_id, "ok": ok, "detail": detail})
        if not ok:
            bugs.append(
                {
                    "id": f"BUG-{len(bugs) + 1:03d}",
                    "severity": severity,
                    "summary": detail,
                    "steps": [check_id],
                    "expected": "success",
                    "actual": detail,
                    "area": check_id.split(".")[0],
                }
            )

    health = client.get("/healthz")
    check("app.healthz", health.status_code == 200, health.text[:200], severity="blocker")

    me = client.get("/api/me", headers=headers)
    check("auth.me", me.status_code == 200 and me.json().get("id") == user.id, me.text[:200])

    created = client.post(
        "/api/conversations",
        headers=headers,
        json={
            "name": "Explaining a flaky deploy to my team",
            "feedback_expectations": "Prefer SRE incident vocabulary",
        },
    )
    check(
        "conversation.create",
        created.status_code == 200
        and created.json().get("feedback_expectations") == "Prefer SRE incident vocabulary",
        created.text[:200],
    )
    conversation_id = created.json().get("id") if created.status_code == 200 else None

    listed = client.get("/api/conversations", headers=headers)
    if listed.status_code == 200:
        ids = [c["id"] for c in listed.json().get("conversations", [])]
    else:
        ids = []
    check(
        "conversation.list",
        listed.status_code == 200 and conversation_id in ids,
        listed.text[:200],
    )

    use_fake(
        FakeLLM(
            fixtures={
                "editor": EDITOR_FIXTURE,
                "partner": "What part of the deploy felt unclear?",
                "usage_judge": '{"correct": true, "explanation": "ok"}',
                "drill_gen": json.dumps(
                    {
                        "vague_sentence": "We need to fix the flaky job.",
                        "intended_option_id": "fix.repair/resolve",
                        "intended_word": "resolve",
                    }
                ),
                "drill_grade": json.dumps(
                    {
                        "precision": 4,
                        "meaning": 4,
                        "naturalness": 4,
                        "feedback": "Clear.",
                        "better_version": None,
                        "used_option_id": "fix.repair/resolve",
                    }
                ),
            },
            stream_chunks={"partner": ["What ", "part?"]},
        )
    )

    if conversation_id:
        posted = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": "The deploy had a big hard problem near the end."},
        )
        check("conversation.post_message", posted.status_code == 200, posted.text[:200])
        message_id = posted.json().get("id") if posted.status_code == 200 else None

        if message_id:
            with client.stream(
                "GET",
                f"/api/conversations/{conversation_id}/messages/{message_id}/partner",
                headers=headers,
            ) as stream:
                body = b"".join(stream.iter_bytes())
            check(
                "conversation.partner_sse",
                stream.status_code == 200 and b"part" in body.lower(),
                body[:200].decode(errors="replace"),
            )

            feedback = client.get(
                f"/api/conversations/{conversation_id}/messages/{message_id}/feedback",
                headers=headers,
            )
            fb = feedback.json() if feedback.status_code == 200 else {}
            suggestions = fb.get("suggestions") or []
            check(
                "conversation.feedback",
                feedback.status_code == 200
                and not fb.get("failed")
                and isinstance(fb.get("overview"), str)
                and "highlighted_html" in fb
                and len(suggestions) >= 1,
                str(fb)[:300],
            )

            if suggestions:
                first = suggestions[0]
                opt = (first.get("options") or [{}])[0]
                accepted = client.post(
                    f"/api/conversations/{conversation_id}/suggestions/{first['id']}/accept",
                    headers=headers,
                    json={"option_id": opt.get("id")},
                )
                check("conversation.accept", accepted.status_code == 200, accepted.text[:200])

    dash = client.get("/api/dashboard", headers=headers)
    dash_body = dash.json() if dash.status_code == 200 else {}
    metric_keys = ("crutch_rate", "acceptance", "spontaneous", "misuse", "mtld")
    check(
        "dashboard.keys",
        dash.status_code == 200 and all(k in dash_body for k in metric_keys),
        str(dash_body)[:200],
    )

    review = client.get("/api/review", headers=headers)
    check("review.get", review.status_code == 200 and "option" in review.json(), review.text[:200])

    # Drills need at least one SRS card so the selector has a group.
    ensure_card(session, user_id=user.id, option_id="fix.repair/resolve")
    drill = client.post("/api/drills", headers=headers)
    check(
        "drills.create",
        drill.status_code == 200 and "vague_sentence" in drill.json(),
        drill.text[:200],
    )

    exported = client.get("/account/export")
    check(
        "account.export",
        exported.status_code == 200 and exported.json().get("user", {}).get("id") == user.id,
        exported.text[:200],
        severity="minor",
    )

    if conversation_id:
        deleted = client.delete(f"/api/conversations/{conversation_id}", headers=headers)
        check("conversation.delete", deleted.status_code == 204, deleted.text[:200])

    status = "pass" if not bugs else "fail"
    _write_report(status=status, checks=checks, bugs=bugs)
    assert status == "pass", bugs
