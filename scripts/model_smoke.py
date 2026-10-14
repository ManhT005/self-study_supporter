"""Opt-in real BGE-M3/Ollama smoke in an isolated synthetic account."""

import json
import uuid
from pathlib import Path

import fitz

from src.agent.orchestrator import ReActOrchestrator
from src.agent.tools.generate_quiz import GenerateQuizTool
from src.agent.tools.search_docs import SearchDocsTool
from src.auth.auth_service import authenticate_user, register_user
from src.db.lifecycle import verify_schema
from src.documents.document_service import (
    create_document,
    get_latest_ready_document,
    update_document_status,
)
from src.llm.ollama_client import OllamaClient
from src.memory.progress_db import ProgressDB
from src.rag.bm25_index import BM25Index
from src.rag.chunker import (
    compute_breakpoints,
    compute_distances,
    embed_sentences,
    flatten_pages_to_sentences,
    group_sentences_into_chunks,
)
from src.rag.embedder import embed_chunks
from src.rag.embedding_provider import LocalEmbeddingProvider
from src.rag.hybrid_retriever import hybrid_search
from src.rag.pdf_parser import parse_pdf
from src.rag.vector_store import VectorStore
from ui.components.quiz_arena import _parse_quiz_from_text


def main():
    verify_schema()
    provider = LocalEmbeddingProvider()
    suffix, password = uuid.uuid4().hex[:12], uuid.uuid4().hex
    username = f"model-smoke-{suffix}"
    user_id = register_user(username, password)
    assert authenticate_user(username, password) == user_id
    path = Path(f"data/model-fixture-{suffix}.pdf")
    content = "A computer network connects devices to exchange data. A router forwards data between networks. A switch connects devices within a local network."
    with fitz.open() as pdf:
        pdf.new_page().insert_textbox(fitz.Rect(72, 72, 500, 500), content)
        pdf.save(path)
    try:
        pages = parse_pdf(str(path)).pages
        sentences = embed_sentences(flatten_pages_to_sentences(pages), provider)
        chunks = group_sentences_into_chunks(
            sentences, compute_breakpoints(sentences, compute_distances(sentences))
        )
        assert chunks
        vectors = embed_chunks(chunks, provider)
        assert len(vectors[0]) == 1024
        document_id, collection = create_document(user_id, path.name)
        store = VectorStore(collection_name=collection)
        store.add_chunks(chunks, vectors)
        update_document_status(
            document_id, "ready", page_count=1, chunk_count=len(chunks), user_id=user_id
        )
        bm25 = BM25Index(chunks)

        def embed_query(text):
            return provider.embed([text], "RETRIEVAL_QUERY")[0]

        retrieved = hybrid_search("What does a router do?", store, bm25, embed_query, top_k=1)
        assert retrieved and retrieved[0].source == path.name
        llm = OllamaClient(model="qwen3:1.7b")
        search = SearchDocsTool(store, bm25, embed_query, document_id=str(document_id))
        result = ReActOrchestrator(llm, [search]).run(
            "Use search_docs to explain what a router does, based only on the uploaded document."
        )
        assert result.final_answer.strip() and search.last_evidence
        quiz = _parse_quiz_from_text(GenerateQuizTool(llm).run(content, num_questions=1))
        assert quiz and len(quiz) == 1
        ProgressDB().record_attempt(
            str(user_id), "networking", quiz[0]["question"], True, document_id
        )
        assert ProgressDB().get_summary(str(user_id))["total_attempts"] == 1
        assert get_latest_ready_document(user_id)["id"] == document_id
        Path("data/p0-real-model-smoke.json").write_text(
            json.dumps(
                {
                    "user_id": user_id,
                    "document_id": document_id,
                    "collection": collection,
                    "chunk_count": len(chunks),
                }
            ),
            encoding="utf-8",
        )
        print(
            "PASS: real BGE-M3 1024D PDF ingestion, hybrid retrieval, Ollama ReAct/evidence, valid quiz and persisted progress"
        )
        print(
            "Provider smoke is synthetic-account service execution, not browser E2E or a quality benchmark"
        )
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
