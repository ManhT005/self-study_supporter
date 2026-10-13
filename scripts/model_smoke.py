"""Opt-in real BGE-M3/Ollama execution through the canonical application facade."""

import json
import os
import uuid
from dataclasses import replace
from pathlib import Path

import fitz

from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.application.contracts.learning import IngestDocumentRequest, QuizRequest
from study_supporter.application.contracts.retrieval import RetrievalQuery


def main():
    settings = replace(Settings.from_mapping(os.environ), ollama_model="qwen3:1.7b")
    with ApplicationFactory(settings) as services:
        services.verify_schema()
        suffix, password = uuid.uuid4().hex[:12], uuid.uuid4().hex
        username = f"model-smoke-{suffix}"
        context = services.authentication.register(username, password)
        assert services.authentication.authenticate(username, password) == context
        content = "A computer network connects devices to exchange data. A router forwards data between networks. A switch connects devices within a local network."
        filename = f"model-fixture-{suffix}.pdf"
        with fitz.open() as pdf:
            pdf.new_page().insert_textbox(fitz.Rect(72, 72, 500, 500), content)
            uploaded = pdf.tobytes()
        document = services.ingestion.execute(IngestDocumentRequest(context, filename, uploaded))
        session = services.open_document(context, document.document_id, mode="ollama")
        evidence = services.retriever().execute(
            RetrievalQuery(
                context.user_id, session.context.active_document_ids, "What does a router do?", 1
            )
        )
        assert evidence and evidence[0].source == filename
        assert len(services.embedding.embed(["router"], "RETRIEVAL_QUERY")[0]) == 1024
        answer = session.answer(
            "Use search_docs to explain what a router does, based only on the uploaded document."
        )
        assert answer.answer.strip() and answer.evidences
        quiz = session.generate_quiz(QuizRequest(session.context, 1, "networking"))
        assert len(quiz) == 1
        assert session.submit_quiz(quiz[0], quiz[0]["correct_index"]).is_correct
        assert session.progress()["total_attempts"] == 1
        Path("data/real-model-smoke.json").write_text(
            json.dumps(
                {
                    "user_id": context.user_id,
                    "document_id": document.document_id,
                    "chunk_count": document.chunk_count,
                    "trace_id": answer.trace_id,
                }
            ),
            encoding="utf-8",
        )
    print(
        "PASS: real BGE-M3 1024D ingestion/retrieval, Ollama ReAct/evidence/quiz, persisted progress"
    )
    print(
        "Synthetic account service execution; browser acceptance and quality benchmarks are separate"
    )


if __name__ == "__main__":
    main()
