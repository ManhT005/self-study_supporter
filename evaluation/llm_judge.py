from pydantic import BaseModel
from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.ai.assessment.json_parsing import parse_llm_model


class JudgeScore(BaseModel):
    faithfulness: int  # 1-5: có bám sát đáp án tham chiếu, không bịa đặt
    relevance: int  # 1-5: có đúng trọng tâm câu hỏi
    reasoning: str  # giải thích ngắn vì sao chấm điểm như vậy


JUDGE_PROMPT = """Bạn là người chấm điểm khách quan cho hệ thống AI trợ giảng. Đánh giá câu trả lời sau theo 2 tiêu chí, mỗi tiêu chí từ 1-5 điểm:

- faithfulness (1-5): Câu trả lời có bám sát đáp án tham chiếu, không bịa đặt/sai lệch thông tin không? 5 = hoàn toàn chính xác, 1 = sai nghiêm trọng hoặc bịa đặt.
- relevance (1-5): Câu trả lời có đúng trọng tâm câu hỏi, không lạc đề không? 5 = đúng trọng tâm hoàn toàn, 1 = lạc đề hoàn toàn.

Câu hỏi: {question}
Đáp án tham chiếu: {reference_answer}
Câu trả lời cần chấm: {answer}

Chỉ trả về JSON, KHÔNG markdown fence, đúng format:
{{"faithfulness": <1-5>, "relevance": <1-5>, "reasoning": "..."}}
"""


def judge_answer(
    question: str,
    reference_answer: str | None,
    answer: str,
    llm: LLMAdapter,
) -> JudgeScore:
    if not answer or not answer.strip():
        return JudgeScore(faithfulness=1, relevance=1, reasoning="Câu trả lời rỗng.")

    ref = reference_answer or (
        "(Không có đáp án tham chiếu cố định — đây là câu hỏi cá nhân hóa, "
        "chấm theo mức độ hợp lý/hữu ích chung của câu trả lời.)"
    )

    prompt = JUDGE_PROMPT.format(question=question, reference_answer=ref, answer=answer)
    response = llm.chat([{"role": "user", "content": prompt}])

    try:
        return parse_llm_model(response.text, JudgeScore)
    except Exception as e:
        return JudgeScore(faithfulness=0, relevance=0, reasoning=f"Lỗi parse judge output: {e}")
