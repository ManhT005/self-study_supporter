import json
import time
from src.eval.llm_judge import judge_answer


def run_judge_on_results(results: list[dict], judge_llm) -> list[dict]:
    """
    Đọc data/eval_results.json (đã có từ eval_runner), chấm điểm cả 2 pipeline
    cho mỗi câu, gắn thêm field "rag_only_score" / "agent_rag_score" vào từng item.
    """
    for item in results:
        question = item["question"]
        reference = item.get("reference_answer")

        rag_score = judge_answer(question, reference, item["rag_only"]["answer"], judge_llm)
        item["rag_only"]["score"] = rag_score.model_dump()

        agent_score = judge_answer(question, reference, item["agent_rag"]["answer"], judge_llm)
        item["agent_rag"]["score"] = agent_score.model_dump()

        print(f"[{item['id']}] RAG-only: F={rag_score.faithfulness} R={rag_score.relevance} | "
              f"Agent+RAG: F={agent_score.faithfulness} R={agent_score.relevance}")

    return results


if __name__ == "__main__":
    with open("data/eval_results.json", encoding="utf-8") as f:
        results = json.load(f)

    # judge_llm nên là GeminiClient — model đủ tốt để chấm điểm đáng tin,
    # KHÔNG dùng Ollama 1.5B để chấm (model quá yếu, điểm số sẽ không đáng tin cậy)
    from google import genai
    from src.llm.gemini_client import GeminiClient
    import os
    from dotenv import load_dotenv

    load_dotenv()
    judge_llm = GeminiClient(genai.Client(api_key=os.getenv("GEMINI_API_KEY")))

    judged_results = run_judge_on_results(results, judge_llm)

    with open("data/eval_results_judged.json", "w", encoding="utf-8") as f:
        json.dump(judged_results, f, ensure_ascii=False, indent=2)

    print("\nĐã lưu data/eval_results_judged.json")