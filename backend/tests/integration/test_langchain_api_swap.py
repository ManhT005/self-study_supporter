import pytest

pytest.importorskip("langchain")

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from apps.api.app.main import HTTPSettings, create_app
from apps.api.tests.fixtures import FixtureFactory
from scripts.docker_smoke import fixture_pdf
from scripts.langchain_fixtures import ScriptedNativeModel, native_call
from study_supporter.application.use_cases.learning import GetProgressUseCase
from study_supporter.orchestration.langchain_agent.adapter import LangChainAgentFactory


def test_real_http_swap_scoped_retrieval_and_legacy_rollback(tmp_path):
    factory = FixtureFactory(f"sqlite:///{tmp_path / 'native-http.db'}")
    models = []

    def model_factory():
        model = ScriptedNativeModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        native_call("search_docs", {"query": "First sentence"}, "search"),
                        native_call("get_progress", {}, "progress"),
                    ],
                ),
                AIMessage(content="Native supported answer"),
            ]
        )
        models.append(model)
        return model

    factory._agent_factory = LangChainAgentFactory(
        model_factory, GetProgressUseCase(factory.progress_repository)
    )
    app = create_app(lambda: factory, HTTPSettings("http://testserver", False))
    with TestClient(app, headers={"origin": "http://testserver"}) as client:
        credentials = {"username": "alice", "password": "fixture-password"}
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
        assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
        doc = client.post(
            "/api/v1/documents", files={"file": ("fixture.pdf", fixture_pdf(), "application/pdf")}
        ).json()
        path = f"/api/v1/documents/{doc['id']}/chat"
        native = client.post(path, json={"question": "First sentence?"})
        assert native.status_code == 200, native.text
        payload = native.json()
        assert set(payload) == {"answer", "citations", "trace_id"}
        assert payload["answer"] == "Native supported answer"
        assert payload["citations"][0]["document_id"] == str(doc["id"])
        assert "tool_calls" not in payload and "usage" not in payload
        assert factory.stores[doc["id"]].notes == []
        assert len(models) == 1
        bob = {"username": "bobby", "password": "fixture-password"}
        assert client.post("/api/v1/auth/register", json=bob).status_code == 201
        assert client.post("/api/v1/auth/login", json=bob).status_code == 200
        assert client.post(path, json={"question": "Alice secret?"}).status_code == 404
        assert len(models) == 1
        assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
        factory._agent_factory = None
        legacy = client.post(path, json={"question": "First sentence?"})
        assert legacy.status_code == 200 and set(legacy.json()) == set(payload)
        assert len(models) == 1


def test_offline_smoke_uses_no_network_even_with_inherited_tracing_enabled(monkeypatch):
    import socket
    import sys

    from scripts.langchain_smoke import run_smoke

    original_connect = socket.socket.connect

    def deny_network(sock, address):
        caller = sys._getframe(1)
        # Windows asyncio implements its internal wakeup socketpair via loopback.
        # Only stdlib's socketpair construction may connect; providers remain blocked.
        if (
            sys.platform == "win32"
            and caller.f_code.co_name == "_fallback_socketpair"
            and caller.f_globals.get("__name__") == "socket"
        ):
            return original_connect(sock, address)
        raise AssertionError("Offline fixture attempted external network access")

    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    for key in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"]:
        monkeypatch.delenv(key, raising=False)
    result = run_smoke()
    assert result["status"] == "passed" and result["authorized_writes"] == 1
    assert result["foreign_evidences"] == 0 and result["legacy_default"]
