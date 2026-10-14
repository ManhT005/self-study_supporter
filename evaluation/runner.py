"""Opt-in online comparison on a dedicated account's owned document."""

import argparse
import os
from dataclasses import replace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, help="Dedicated fixture account ID")
    parser.add_argument("--dataset", default="data/eval_dataset.json")
    parser.add_argument("--output", default="data/eval_results.json")
    args = parser.parse_args()
    from dotenv import load_dotenv
    from study_supporter.bootstrap import ApplicationFactory
    from study_supporter.config import Settings
    from study_supporter.application.contracts.context import AppContext
    from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
    from study_supporter.orchestration.legacy_react.tools.generate_quiz import GenerateQuizTool
    from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import (
        RetrieveEvidenceTool,
    )
    from study_supporter.orchestration.legacy_react.tools.save_note import SaveNoteTool
    from study_supporter.orchestration.legacy_react.tools.get_progress import GetProgressTool
    from study_supporter.application.use_cases.learning import SaveNoteUseCase, GetProgressUseCase
    from study_supporter.infrastructure.persistence.chroma.note_repository import LongTermMemory
    from study_supporter.infrastructure.retrieval.bm25_adapter import BM25Index
    from evaluation.eval_runner import load_eval_dataset, run_eval, save_results

    load_dotenv()
    settings = replace(Settings.from_mapping(os.environ), ollama_model="qwen3:1.7b")
    with ApplicationFactory(settings) as services:
        services.verify_schema()
        context = AppContext(args.user_id)
        document = services.document_repository.latest(context.user_id)
        if document is None:
            parser.error("Evaluation account has no ready document")
        context = AppContext(context.user_id, (str(document["id"]),))
        store = services.vector_store(document)
        chunks = store.load_all_chunks()
        if not chunks:
            parser.error("Document vectors are unavailable")
        llm = services.provider("ollama").client

        def embed_query(question):
            return services.embedding.embed([question], "RETRIEVAL_QUERY")[0]

        tools = [
            RetrieveEvidenceTool(services.retriever(), context),
            GenerateQuizTool(llm),
            SaveNoteTool(SaveNoteUseCase(LongTermMemory(store, embed_query)), context.user_id),
            GetProgressTool(GetProgressUseCase(services.progress_repository), context.user_id),
        ]
        # The experimental comparison retains iteration/tool metrics and personalized history.
        agent = ReActOrchestrator(llm, tools)
        results = run_eval(
            load_eval_dataset(args.dataset)[:5], store, BM25Index(chunks), embed_query, llm, agent
        )
        save_results(results, args.output)
    print(f"Saved {len(results)} evaluation results; online model calls were explicitly requested.")


if __name__ == "__main__":
    main()
