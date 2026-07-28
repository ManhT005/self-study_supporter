import json


def compute_summary(judged_results: list[dict]) -> dict:
    summary = {
        "overall": {"rag_only": {"faithfulness": [], "relevance": []},
                    "agent_rag": {"faithfulness": [], "relevance": []}},
        "by_category": {},
    }

    for item in judged_results:
        category = item["category"]
        if category not in summary["by_category"]:
            summary["by_category"][category] = {
                "rag_only": {"faithfulness": [], "relevance": []},
                "agent_rag": {"faithfulness": [], "relevance": []},
            }

        for pipeline in ("rag_only", "agent_rag"):
            score = item[pipeline].get("score")
            if not score:
                continue
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
                "n": len(vals["faithfulness"]),
            }
            for pipeline, vals in d.items()
        }

    result = {
        "overall": _finalize(summary["overall"]),
        "by_category": {cat: _finalize(d) for cat, d in summary["by_category"].items()},
    }
    return result


def print_summary_table(summary: dict) -> None:
    print("=" * 60)
    print("TỔNG QUAN (toàn bộ câu hỏi)")
    print("=" * 60)
    for pipeline, stats in summary["overall"].items():
        print(f"{pipeline:12s} | Faithfulness: {stats['avg_faithfulness']} | "
              f"Relevance: {stats['avg_relevance']} | n={stats['n']}")

    print("\n" + "=" * 60)
    print("THEO CATEGORY")
    print("=" * 60)
    for category, pipelines in summary["by_category"].items():
        print(f"\n--- {category} ---")
        for pipeline, stats in pipelines.items():
            print(f"  {pipeline:12s} | Faithfulness: {stats['avg_faithfulness']} | "
                  f"Relevance: {stats['avg_relevance']} | n={stats['n']}")


if __name__ == "__main__":
    with open("data/eval_results_judged.json", encoding="utf-8") as f:
        judged_results = json.load(f)

    summary = compute_summary(judged_results)
    print_summary_table(summary)

    with open("data/eval_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)