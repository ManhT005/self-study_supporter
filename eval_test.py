"""Opt-in online evaluation against a dedicated authenticated fixture account."""

import argparse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user-id", required=True, type=int, help="Dedicated evaluation account ID"
    )
    parser.add_argument("--dataset", default="data/eval_dataset.json")
    parser.add_argument("--output", default="data/eval_results_test1.json")
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv()
    from src.db.lifecycle import verify_schema
    from src.documents.document_service import get_latest_ready_document
    from src.agent.orchestrator import ReActOrchestrator
    from src.agent.tools.generate_quiz import GenerateQuizTool
    from src.agent.tools.get_progress import GetProgressTool
    from src.agent.tools.save_note import SaveNoteTool
    from src.agent.tools.search_docs import SearchDocsTool
    from src.eval.eval_runner import load_eval_dataset, run_eval, save_results
    from src.llm.ollama_client import OllamaClient
    from src.memory.long_term import LongTermMemory
    from src.memory.progress_db import ProgressDB
    from src.rag.bm25_index import BM25Index
    from src.rag.embedding_provider import LocalEmbeddingProvider
    from src.rag.vector_store import VectorStore

    verify_schema()
    document = get_latest_ready_document(args.user_id)
    if document is None:
        parser.error("Evaluation account has no ready document")
    store = VectorStore(collection_name=document["chroma_collection_name"])
    chunks = store.load_all_chunks()
    if not chunks:
        parser.error("Document vectors are unavailable")
    bm25 = BM25Index(chunks)
    provider = LocalEmbeddingProvider()  # Preserve BGE-M3 / 1024D baseline.

    def embed_query_fn(question):
        return provider.embed([question], task_type="RETRIEVAL_QUERY")[0]

    llm = OllamaClient(model="qwen3:1.7b")
    memory = LongTermMemory(store, embed_query_fn)
    progress = ProgressDB()
    identity = str(args.user_id)
    tools = [
        SearchDocsTool(store, bm25, embed_query_fn, document_id=str(document["id"])),
        GenerateQuizTool(llm),
        SaveNoteTool(memory, identity),
        GetProgressTool(progress, identity),
    ]
    orchestrator = ReActOrchestrator(llm, tools)
    dataset = load_eval_dataset(args.dataset)
    results = run_eval(dataset[:5], store, bm25, embed_query_fn, llm, orchestrator)
    save_results(results, args.output)
    print(f"Saved {len(results)} evaluation results; online model calls were explicitly requested.")


if __name__ == "__main__":
    main()
