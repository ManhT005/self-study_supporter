"""Explicit synthetic-provider acceptance against real container storage/HTTP."""

import argparse
import json
import os
import uuid
from pathlib import Path

import requests

from apps.api.app.main import create_app
from scripts.docker_smoke import FakeEmbedding, FakeLLM, fixture_pdf
from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.infrastructure.llm.factory import ProviderSelection

MARKER = Path("data/workspace-http-smoke.json")


def create_smoke_app():
    return create_app(
        lambda: ApplicationFactory(
            Settings.from_mapping(os.environ),
            embedding=FakeEmbedding(),
            provider_factory=lambda settings, mode: ProviderSelection(FakeLLM(), "ollama"),
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify"])
    args = parser.parse_args()
    base = "http://web:3000/api/v1"
    http = requests.Session()
    http.headers["Origin"] = os.getenv("WEB_ORIGIN", "http://localhost:3000")

    def call(method, path, expected=200, **kwargs):
        response = http.request(method, base + path, timeout=120, **kwargs)
        if response.status_code != expected:
            # Only a safe code, never print credentials/provider messages.
            raise AssertionError(f"HTTP {response.status_code} for {method} {path}")
        return response.json() if response.content else None

    if args.action == "seed":
        if MARKER.exists():
            parser.error("Use verify for existing synthetic state")
        state = {"username": "http-" + uuid.uuid4().hex[:16], "password": uuid.uuid4().hex}
        call("POST", "/auth/register", 201, json=state)
        call("POST", "/auth/login", json=state)
        doc = call(
            "POST",
            "/documents",
            201,
            files={"file": ("fixture.pdf", fixture_pdf(), "application/pdf")},
        )
        state["document_id"] = doc["id"]
        path = f"/documents/{doc['id']}"
        assert doc["status"] == "ready"
        quiz = call("POST", path + "/quizzes", json={"num_questions": 1})
        assert "correct_index" not in quiz["questions"][0]
        submit = path + f"/quizzes/{quiz['quiz_id']}/attempts"
        answer = {"question_index": 0, "selected_index": 1}
        assert call("POST", submit, json=answer)["is_correct"]
        assert call("POST", submit, json=answer)["is_correct"]
        MARKER.write_text(json.dumps(state), encoding="utf-8")
    else:
        state = json.loads(MARKER.read_text(encoding="utf-8"))
        call("POST", "/auth/login", json={k: state[k] for k in ["username", "password"]})
    path = f"/documents/{state['document_id']}"
    assert call("GET", path)["status"] == "ready"
    assert call("GET", path + "/reader")[0]["page_start"] == 1
    answer = call("POST", path + "/chat", json={"question": "First sentence?"})
    assert answer["citations"][0]["source"] == "fixture.pdf"
    assert answer["citations"][0]["page_start"] == 1
    assert call("GET", "/progress")["total_attempts"] == 1
    call("POST", "/auth/logout", 204)
    call("GET", path, 401)
    print("PASS: real web/API HTTP, PostgreSQL/Chroma, citations and idempotent quiz progress")


if __name__ == "__main__":
    main()
