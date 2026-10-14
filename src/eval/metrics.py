import json

import numpy as np


def compute_summary(judged_results: list[dict]) -> dict:
    summary = {
        "overall": {"rag_only": {"faithfulness": [], "relevance": [], "parse_errors": 0},
                    "agent_rag": {"faithfulness": [], "relevance": [], "parse_errors": 0}},
        "by_category": {},
    }

    for item in judged_results:
        category = item["category"]
        if category not in summary["by_category"]:
            summary["by_category"][category] = {
                "rag_only": {"faithfulness": [], "relevance": [], "parse_errors": 0},
                "agent_rag": {"faithfulness": [], "relevance": [], "parse_errors": 0},
            }

        for pipeline in ("rag_only", "agent_rag"):
            score = item[pipeline].get("score")
            if not score:
                continue
            if score["faithfulness"] == 0 and score["relevance"] == 0:
                summary["overall"][pipeline]["parse_errors"] += 1
                summary["by_category"][category][pipeline]["parse_errors"] += 1
                continue  # KHÔNG đưa vào danh sách tính trung bình
            summary["overall"][pipeline]["faithfulness"].append(score["faithfulness"])
            summary["overall"][pipeline]["relevance"].append(score["relevance"])
            summary["by_category"][category][pipeline]["faithfulness"].append(score["faithfulness"])
            summary["by_category"][category][pipeline]["relevance"].append(score["relevance"])

    def _avg(lst):
        return round(sum(lst) / len(lst), 2) if lst else None

    def _finalize(d):
        return {
            pipeline: {
                "avg_faithfulness": _avg(vals["faithfulness"]),
                "avg_relevance": _avg(vals["relevance"]),
                "n_scored": len(vals["faithfulness"]),
                "parse_errors": vals["parse_errors"],
            }
            for pipeline, vals in d.items()
        }

    return {
        "overall": _finalize(summary["overall"]),
        "by_category": {cat: _finalize(d) for cat, d in summary["by_category"].items()},
    }

def print_summary_table(summary: dict) -> None:
    print("=" * 60)
    print("TỔNG QUAN (toàn bộ câu hỏi)")
    print("=" * 60)
    for pipeline, stats in summary["overall"].items():
        print(f"{pipeline:12s} | Faithfulness: {stats['avg_faithfulness']} | "
              f"Relevance: {stats['avg_relevance']} | n_scored={stats['n_scored']} | "
              f"parse_errors={stats['parse_errors']}")

    print("\n" + "=" * 60)
    print("THEO CATEGORY")
    print("=" * 60)
    for category, pipelines in summary["by_category"].items():
        print(f"\n--- {category} ---")
        for pipeline, stats in pipelines.items():
            print(f"  {pipeline:12s} | Faithfulness: {stats['avg_faithfulness']} | "
                  f"Relevance: {stats['avg_relevance']} | n_scored={stats['n_scored']} | "
                  f"parse_errors={stats['parse_errors']}")

def cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def compute_similarity_score(reference_answer: str | None, answer: str, provider) -> float | None:
    if not reference_answer:
        return None
    ref_emb = provider.embed([reference_answer], task_type="SEMANTIC_SIMILARITY")[0]
    ans_emb = provider.embed([answer], task_type="SEMANTIC_SIMILARITY")[0]
    return round(cosine_similarity(ref_emb, ans_emb), 3)

def compute_similarity_for_results(results: list[dict], provider) -> list[dict]:
    """
    Tính cosine similarity giữa answer và reference_answer cho mỗi câu
    (chỉ áp dụng được với factual/reasoning, personalized sẽ có similarity=None).
    Ghi trực tiếp vào results, trả về results đã cập nhật.
    """
    for item in results:
        reference = item.get("reference_answer")
        for pipeline in ("rag_only", "agent_rag"):
            answer = item[pipeline]["answer"]
            item[pipeline]["similarity"] = compute_similarity_score(reference, answer, provider)
    return results


def compute_similarity_summary(results: list[dict]) -> dict:
    summary = {"overall": {"rag_only": [], "agent_rag": []}, "by_category": {}}

    for item in results:
        category = item["category"]
        if category not in summary["by_category"]:
            summary["by_category"][category] = {"rag_only": [], "agent_rag": []}

        for pipeline in ("rag_only", "agent_rag"):
            sim = item[pipeline].get("similarity")
            if sim is None:
                continue
            summary["overall"][pipeline].append(sim)
            summary["by_category"][category][pipeline].append(sim)

    def _avg(lst):
        return round(sum(lst) / len(lst), 3) if lst else None

    return {
        "overall": {p: _avg(v) for p, v in summary["overall"].items()},
        "by_category": {
            cat: {p: _avg(v) for p, v in d.items()} for cat, d in summary["by_category"].items()
        },
    }


def print_similarity_table(summary: dict) -> None:
    print("\n" + "=" * 60)
    print("COSINE SIMILARITY (answer vs reference_answer) — không cần LLM")
    print("=" * 60)
    print("Overall:")
    for pipeline, avg in summary["overall"].items():
        print(f"  {pipeline:12s} | avg similarity: {avg}")

    print("\nTheo category:")
    for category, pipelines in summary["by_category"].items():
        print(f"  --- {category} ---")
        for pipeline, avg in pipelines.items():
            print(f"    {pipeline:12s} | avg similarity: {avg}")

if __name__ == "__main__":
    with open("data/eval_results_judged.json", encoding="utf-8") as f:
        judged_results = json.load(f)

    # --- Phần LLM-judge (đã có) ---
    summary = compute_summary(judged_results)
    print_summary_table(summary)

    # --- Phần cosine similarity (mới, không tốn quota) ---
    from src.rag.embedding_provider import LocalEmbeddingProvider
    provider = LocalEmbeddingProvider()

    judged_results = compute_similarity_for_results(judged_results, provider)
    similarity_summary = compute_similarity_summary(judged_results)
    print_similarity_table(similarity_summary)

    # --- Lưu lại tất cả, bao gồm cả similarity vừa tính ---
    with open("data/eval_results_judged.json", "w", encoding="utf-8") as f:
        json.dump(judged_results, f, ensure_ascii=False, indent=2)

    with open("data/eval_summary.json", "w", encoding="utf-8") as f:
        json.dump({"llm_judge": summary, "similarity": similarity_summary}, f, ensure_ascii=False, indent=2)