import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import HTTPSettings, create_app
from apps.api.tests.fixtures import FixtureFactory
from scripts.docker_smoke import fixture_pdf
from study_supporter.domain.errors import EmbeddingUnavailable, QuotaExceeded

PDF = fixture_pdf()


@pytest.fixture
def http(tmp_path):
    factory = FixtureFactory(f"sqlite:///{tmp_path / 'http.db'}")
    app = create_app(lambda: factory, HTTPSettings("http://testserver", False))
    with TestClient(app, headers={"origin": "http://testserver"}) as client:
        credentials = {"username": "alice", "password": "fixture-password"}
        assert client.post("/api/v1/auth/register", json=credentials).status_code == 201
        assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
        yield client, factory


def upload(client, name="fixture.pdf", content=None):
    return client.post(
        "/api/v1/documents",
        files={"file": (name, PDF if content is None else content, "application/pdf")},
    )


def test_complete_learning_slice_and_cross_account_isolation(http):
    client, factory = http
    assert client.get("/api/v1/documents").json() == []
    response = upload(client)
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc["status"] == "ready" and doc["chunk_count"] > 0
    assert upload(client).json()["id"] == doc["id"]
    path = f"/api/v1/documents/{doc['id']}"
    assert client.get(f"{path}/reader").json()[0]["page_start"] == 1
    answer = client.post(f"{path}/chat", json={"question": "First sentence?"})
    assert answer.status_code == 200, answer.text
    citation = answer.json()["citations"][0]
    assert citation["source"] == "fixture.pdf" and citation["document_id"] == str(doc["id"])
    assert set(answer.json()) == {"answer", "citations", "trace_id"}
    quiz = client.post(f"{path}/quizzes", json={"num_questions": 1}).json()
    assert len(quiz["questions"][0]["options"]) == 4
    assert "correct_index" not in quiz["questions"][0]
    attempt = f"{path}/quizzes/{quiz['quiz_id']}/attempts"
    selection = {"question_index": 0, "selected_index": 1}
    assert client.post(attempt, json=selection).json()["is_correct"]
    assert client.post(attempt, json=selection).status_code == 200
    assert client.get("/api/v1/progress").json()["total_attempts"] == 1
    assert client.post(attempt, json={**selection, "selected_index": 0}).status_code == 409
    assert client.post(attempt, json={**selection, "selected_index": True}).status_code == 422
    assert client.post(f"{path}/notes", json={"note": "Remember this"}).status_code == 201
    assert factory.stores[doc["id"]].notes[0]["metadatas"] == [{"user_id": "1"}]
    assert client.get(f"{path}/learning-path").json() == {"concepts": [], "has_cycle": False}
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get(path).status_code == 401
    bob = {"username": "bobby", "password": "fixture-password"}
    client.post("/api/v1/auth/register", json=bob)
    client.post("/api/v1/auth/login", json=bob)
    for suffix in ["", "/reader", "/learning-path"]:
        assert client.get(path + suffix).status_code == 404
    assert client.post(f"{path}/chat", json={"question": "First?"}).status_code == 404
    assert client.post(attempt, json=selection).status_code == 404
    assert client.get("/api/v1/documents").json() == []
    assert client.get("/api/v1/progress").json()["total_attempts"] == 0


def test_invalid_pdf_failed_retry_and_provider_error(http, monkeypatch):
    client, factory = http
    assert upload(client, content=b"not pdf").status_code == 422
    assert upload(client, content=fixture_pdf(True)).status_code == 422
    assert upload(client, name="fixture.txt").status_code == 422
    assert upload(client, content=b"%PDF-" + b"x" * (21 * 1024 * 1024)).status_code == 413
    assert all(d["status"] == "failed" for d in client.get("/api/v1/documents").json())
    original = factory.embedding.embed

    def fail(*args, **kwargs):
        raise EmbeddingUnavailable("secret-provider-data")

    monkeypatch.setattr(factory.embedding, "embed", fail)
    failure = upload(client)
    assert failure.status_code == 503 and "secret-provider-data" not in failure.text
    monkeypatch.setattr(factory.embedding, "embed", original)
    doc = upload(client).json()

    def quota(*args):
        raise QuotaExceeded("secret-provider-key")

    monkeypatch.setattr(factory, "provider", quota)
    failure = client.post(f"/api/v1/documents/{doc['id']}/chat", json={"question": "First?"})
    assert failure.status_code == 429 and "secret-provider-key" not in failure.text


def test_startup_recovers_processing_and_cyclic_graph_falls_back(http):
    client, factory = http
    context = factory.authentication.authenticate("alice", "fixture-password")
    interrupted = factory.document_repository.create(context.user_id, "interrupted.pdf")
    assert factory.documents.recover_interrupted() == 1
    assert client.get(f"/api/v1/documents/{interrupted['id']}").json()["status"] == "failed"
    doc = upload(client).json()
    factory.documents.update(
        context,
        doc["id"],
        concept_graph_json={
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
        },
    )
    assert client.get(f"/api/v1/documents/{doc['id']}/learning-path").json() == {
        "concepts": [],
        "has_cycle": True,
    }


def test_agent_can_be_swapped_at_composition_without_changing_http_contract(http, monkeypatch):
    from study_supporter.application.contracts.agent import AgentResult
    from study_supporter.application.contracts.retrieval import RetrievalQuery

    class Agent:
        def __init__(self, context, llm, retriever, tools_factory):
            self.context, self.retriever = context, retriever

        def execute(self, request):
            evidence = tuple(
                self.retriever.execute(
                    RetrievalQuery(
                        self.context.user_id, self.context.active_document_ids, request.question
                    )
                )
            )
            return AgentResult("alternate adapter answer", evidence, "alternate-trace")

    client, factory = http
    monkeypatch.setattr(factory, "_agent_factory", Agent)
    doc = upload(client).json()
    answer = client.post(
        f"/api/v1/documents/{doc['id']}/chat", json={"question": "First sentence?"}
    )
    assert answer.status_code == 200
    assert set(answer.json()) == {"answer", "citations", "trace_id"}
    assert answer.json()["answer"] == "alternate adapter answer"
    assert answer.json()["trace_id"] == "alternate-trace"
    assert answer.json()["citations"][0]["document_id"] == str(doc["id"])


def test_ai_dispatch_releases_admission_slot_after_failure():
    from apps.api.app.learning_services import LearningServices

    services = LearningServices(None)

    def fail():
        raise QuotaExceeded("fixture")

    for _ in range(3):
        with pytest.raises(QuotaExceeded):
            services.call_ai(fail)
    assert services.call_ai(lambda: "success") == "success"


def test_tc_sec_01_02_foreign_chat_note_quiz_never_call_provider_vectors_or_write(
    http, monkeypatch
):
    from unittest.mock import Mock

    client, factory = http
    alice_doc = upload(client).json()
    bob = {"username": "bobby", "password": "fixture-password"}
    assert client.post("/api/v1/auth/register", json=bob).status_code == 201
    assert client.post("/api/v1/auth/login", json=bob).status_code == 200
    bob_doc = upload(client, name="bob.pdf").json()
    bob_context = factory.authentication.authenticate(bob["username"], bob["password"])
    bob_progress = factory.progress_repository.get_summary(bob_context.user_id)
    document_before = factory.document_repository.get(bob_context.user_id, bob_doc["id"])
    store_before = (
        tuple(factory.stores[bob_doc["id"]].chunks),
        tuple(factory.stores[bob_doc["id"]].notes),
    )
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "alice", "password": "fixture-password"}
        ).status_code
        == 200
    )
    provider = Mock(wraps=factory.provider)
    vectors = Mock(wraps=factory.vector_store)
    ranking = Mock(wraps=factory.retriever)
    monkeypatch.setattr(factory, "provider", provider)
    monkeypatch.setattr(factory, "vector_store", vectors)
    monkeypatch.setattr(factory, "retriever", ranking)
    for endpoint, body in [
        ("chat", {"question": "secret?"}),
        ("notes", {"note": "foreign note"}),
        ("quizzes", {"num_questions": 1}),
    ]:
        foreign = client.post(f"/api/v1/documents/{bob_doc['id']}/{endpoint}", json=body)
        missing = client.post(f"/api/v1/documents/999999/{endpoint}", json=body)
        assert foreign.status_code == missing.status_code == 404
        assert {k: v for k, v in foreign.json().items() if k != "request_id"} == {
            k: v for k, v in missing.json().items() if k != "request_id"
        }
        assert "citations" not in foreign.json() and "bob.pdf" not in foreign.text
    provider.assert_not_called()
    vectors.assert_not_called()
    ranking.assert_not_called()
    assert factory.document_repository.get(bob_context.user_id, bob_doc["id"]) == document_before
    assert factory.progress_repository.get_summary(bob_context.user_id) == bob_progress
    assert (
        tuple(factory.stores[bob_doc["id"]].chunks),
        tuple(factory.stores[bob_doc["id"]].notes),
    ) == store_before
    assert client.get(f"/api/v1/documents/{alice_doc['id']}").status_code == 200
