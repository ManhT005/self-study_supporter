"""Functional Docker smoke with synthetic PDF, mocked quiz/LLM and 1024D fake vectors."""

import argparse
import json
import uuid
from pathlib import Path
from unittest.mock import Mock

import fitz

from src.auth.auth_service import authenticate_user, register_user
from src.db.lifecycle import verify_schema
from src.documents.document_service import (
    create_document,
    get_latest_ready_document,
    update_document_status,
)
from src.rag.pdf_parser import parse_pdf
from src.rag.chunker import (
    flatten_pages_to_sentences,
    compute_distances,
    compute_breakpoints,
    group_sentences_into_chunks,
)
from src.rag.vector_store import VectorStore
from src.memory.progress_db import ProgressDB
from src.memory.long_term import LongTermMemory
from src.agent.tools.generate_quiz import GenerateQuizTool
from src.llm.llm_adapter import ChatResponse
from ui.components.quiz_arena import _parse_quiz_from_text
from study_supporter.domain.errors import DocumentUnsupported

MARKER = Path("data/p0-smoke.json")
VECTOR = [1.0] + [0.0] * 1023


def verify(state):
    a, b = state["a"], state["b"]
    assert authenticate_user(state["username"], state["password"]) == a
    doc = get_latest_ready_document(a)
    assert doc and doc["id"] == state["document_id"]
    assert get_latest_ready_document(b) is None
    store = VectorStore(collection_name=doc["chroma_collection_name"])
    assert store.count() == state["chunk_count"]
    result = store.documents.query(query_embeddings=[VECTOR], n_results=1)
    assert result["ids"][0]
    assert result["metadatas"][0][0]["source"] == "fixture.pdf"
    progress = ProgressDB()
    assert progress.get_summary(str(a))["total_attempts"] == 1
    assert progress.get_summary(str(b))["total_attempts"] == 0
    notes = LongTermMemory(store, lambda _: VECTOR)
    assert notes.search_notes(str(a), "question") == ["Synthetic note A"]
    assert notes.search_notes(str(b), "question") == []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify"])
    args = parser.parse_args()
    verify_schema()
    if args.action == "seed":
        if MARKER.exists():
            parser.error("Marker already exists; use verify or a fresh disposable project")
        suffix = uuid.uuid4().hex[:12]
        username, password = f"p0-a-{suffix}", uuid.uuid4().hex
        a = register_user(username, password)
        b = register_user(f"p0-b-{suffix}", uuid.uuid4().hex)
        path = Path("data/fixture.pdf")
        with fitz.open() as pdf:
            pdf.new_page().insert_text((72, 72), "First sentence. Second sentence.")
            pdf.save(path)
        try:
            pages = parse_pdf(str(path)).pages
            sentences = flatten_pages_to_sentences(pages)
            for sentence in sentences:
                sentence.embedding = VECTOR
            chunks = group_sentences_into_chunks(
                sentences, compute_breakpoints(sentences, compute_distances(sentences))
            )
        finally:
            path.unlink(missing_ok=True)
        doc_id, collection = create_document(a, "fixture.pdf")
        store = VectorStore(collection_name=collection)
        store.add_chunks(chunks, [VECTOR for _ in chunks])
        update_document_status(doc_id, "ready", page_count=1, chunk_count=len(chunks), user_id=a)
        llm = Mock()
        llm.chat.return_value = ChatResponse(
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
        quiz = _parse_quiz_from_text(GenerateQuizTool(llm).run(chunks[0].text))
        assert quiz and quiz[0]["correct_index"] == 1
        ProgressDB().record_attempt(str(a), "fixture", quiz[0]["question"], True, doc_id)
        LongTermMemory(store, lambda _: VECTOR).save_note(str(a), "Synthetic note A")
        with fitz.open() as pdf:
            pdf.new_page()
            pdf.save(path)
        try:
            try:
                parse_pdf(str(path))
            except DocumentUnsupported:
                pass
            else:
                raise AssertionError("Blank PDF accepted")
        finally:
            path.unlink(missing_ok=True)
        state = {
            "a": a,
            "b": b,
            "username": username,
            "password": password,
            "document_id": doc_id,
            "chunk_count": len(chunks),
        }
        MARKER.write_text(json.dumps(state), encoding="utf-8")
    else:
        state = json.loads(MARKER.read_text(encoding="utf-8"))
    verify(state)
    print(
        "PASS: SQL/auth, PDF/chunk provenance, persistent Chroma, quiz/progress, A/B ownership and notes"
    )
    print("Synthetic embeddings and mocked LLM; BGE/Ollama/browser E2E remain separate checks")


if __name__ == "__main__":
    main()
