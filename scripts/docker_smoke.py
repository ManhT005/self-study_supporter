"""Opt-in Docker acceptance through public application services and real storage."""

import argparse
import json
import os
import uuid
from pathlib import Path

import fitz

from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import IngestDocumentRequest, QuizRequest
from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.infrastructure.llm.factory import ProviderSelection
from study_supporter.infrastructure.persistence.chroma.note_repository import LongTermMemory
from study_supporter.domain.errors import DocumentUnsupported, EvidenceNotFound

# Keep the existing marker readable to prove historical volume compatibility.
MARKER = Path("data/p0-smoke.json")
VECTOR = [1.0] + [0.0] * 1023


class FakeEmbedding:
    dimension = 1024
    model_id = "BAAI/bge-m3"

    def embed(self, texts, task_type):
        return [list(VECTOR) for _ in texts]


class FakeLLM:
    def chat(self, messages, **kwargs):
        if not kwargs.get("system_prompt"):
            return ChatResponse(
                text=json.dumps(
                    {
                        "questions": [
                            {
                                "question": "Q?",
                                "options": ["a", "b", "c", "d"],
                                "correct_answer_index": 1,
                                "explanation": "fixture",
                            }
                        ]
                    }
                )
            )
        if "Observation:" in messages[-1]["content"]:
            return ChatResponse(text="Final Answer: First sentence. [fixture.pdf, page 1]")
        return ChatResponse(
            text='Action: search_docs\nAction Input: {"query": "First sentence", "top_k": 1}'
        )


def fixture_pdf(blank=False):
    with fitz.open() as pdf:
        page = pdf.new_page()
        if not blank:
            page.insert_text((72, 72), "First sentence. Second sentence.")
        return pdf.tobytes()


def verify(services, state):
    a, b = AppContext(str(state["a"])), AppContext(str(state["b"]))
    assert services.authentication.authenticate(state["username"], state["password"]) == a
    doc = services.document_repository.latest(a.user_id)
    assert doc and doc["id"] == state["document_id"]
    assert services.document_repository.latest(b.user_id) is None
    with_context = AppContext(a.user_id, (str(doc["id"]),))
    evidence = services.retriever().execute(
        RetrievalQuery(a.user_id, with_context.active_document_ids, "First", 3)
    )
    assert evidence and evidence[0].source == "fixture.pdf"
    try:
        services.open_document(b, doc["id"])
    except EvidenceNotFound:
        pass
    else:
        raise AssertionError("Cross-user document access accepted")
    session = services.open_document(a, doc["id"])
    assert session and session.context == with_context
    answer = session.answer("First sentence?")
    assert answer.answer and answer.evidences and answer.trace_id
    assert session.progress()["total_attempts"] == 1
    assert services.progress_repository.get_summary(b.user_id)["total_attempts"] == 0
    store = services.vector_store(doc)
    assert store.count() == state["chunk_count"]
    notes = LongTermMemory(store, lambda _: VECTOR)
    assert notes.search_notes(a.user_id, "question") == ["Synthetic note A"]
    assert notes.search_notes(b.user_id, "question") == []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify"])
    args = parser.parse_args()
    with ApplicationFactory(
        Settings.from_mapping(os.environ),
        embedding=FakeEmbedding(),
        provider_factory=lambda settings, mode: ProviderSelection(FakeLLM(), "ollama"),
    ) as services:
        services.verify_schema()
        if args.action == "seed":
            if MARKER.exists():
                parser.error("Marker exists; use verify or a fresh disposable project")
            suffix, password = uuid.uuid4().hex[:12], uuid.uuid4().hex
            username = f"smoke-a-{suffix}"
            a = services.authentication.register(username, password)
            b = services.authentication.register(f"smoke-b-{suffix}", uuid.uuid4().hex)
            request = IngestDocumentRequest(a, "fixture.pdf", fixture_pdf())
            events = []
            result = services.ingestion.execute(request, events.append)
            assert services.ingestion.execute(request).reused
            assert events[-1].stage.value == "READY"
            assert len({event.trace_id for event in events}) == 1
            session = services.open_document(a, result.document_id)
            quiz = session.generate_quiz(QuizRequest(session.context, 1, "fixture"))
            assert len(quiz) == 1 and quiz[0]["correct_index"] == 1
            assert session.submit_quiz(quiz[0], 1).is_correct
            session.save_note("Synthetic note A")
            try:
                services.ingestion.execute(IngestDocumentRequest(a, "blank.pdf", fixture_pdf(True)))
            except DocumentUnsupported:
                pass
            else:
                raise AssertionError("Blank PDF accepted")
            state = {
                "a": int(a.user_id),
                "b": int(b.user_id),
                "username": username,
                "password": password,
                "document_id": result.document_id,
                "chunk_count": result.chunk_count,
            }
            MARKER.write_text(json.dumps(state), encoding="utf-8")
        else:
            state = json.loads(MARKER.read_text(encoding="utf-8"))
        verify(services, state)
    print(
        "PASS: canonical auth/ingestion/retrieval/chat/quiz/notes/progress, persisted data and A/B isolation"
    )
    print("Synthetic embeddings/LLM; real model and browser checks are separate")


if __name__ == "__main__":
    main()
