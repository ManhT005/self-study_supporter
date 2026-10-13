import json
import time
from evaluation.rag_only import answer_with_rag_only
from study_supporter.infrastructure.retrieval.hybrid_adapter import hybrid_search


def load_eval_dataset(path: str = "data/eval_dataset.json") -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def run_eval(dataset, store, bm25_index, embed_query_fn, llm, orchestrator, top_k=3):
    results = []
    conversation_log = []

    for item in dataset:
        question = item["question"]
        category = item["category"]

        # Chỉ truyền history cho câu personalized — factual/reasoning phải được
        # đánh giá độc lập, không bị nhiễu bởi ngữ cảnh không liên quan.
        history_text = None
        if category == "personalized":
            history_text = "\n".join(conversation_log[-4:])

        t0 = time.time()
        rag_chunks = hybrid_search(question, store, bm25_index, embed_query_fn, top_k=top_k)
        rag_answer = answer_with_rag_only(
            question, store, bm25_index, embed_query_fn, llm, top_k=top_k
        )
        t1 = time.time()

        state = orchestrator.run(question, conversation_history=history_text)
        t2 = time.time()

        results.append(
            {
                "id": item["id"],
                "category": category,
                "question": question,
                "reference_answer": item.get("reference_answer"),
                "rag_only": {
                    "answer": rag_answer,
                    "retrieved_chunk_ids": [c.chunk_id for c in rag_chunks],
                    "time_sec": round(t1 - t0, 2),
                },
                "agent_rag": {
                    "answer": state.final_answer,
                    "iterations": state.iteration,
                    "tools_used": [e.tool_name for e in state.scratchpad if e.type == "action"],
                    "time_sec": round(t2 - t1, 2),
                },
            }
        )

        conversation_log.append(f"Q: {question}\nA: {state.final_answer}")

    return results


def save_results(results: list[dict], path: str = "data/eval_results.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
