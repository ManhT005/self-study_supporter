import json
import re
from pydantic import BaseModel, Field, ValidationError
from src.agent.tools.base import BaseTool
from src.llm.llm_adapter import LLMAdapter


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_answer_index: int
    explanation: str


class GenerateQuizTool(BaseTool):
    name = "generate_quiz"
    description = (
        "Sinh câu hỏi trắc nghiệm dựa trên 1 đoạn nội dung cụ thể, dùng để kiểm tra "
        "kiến thức học sinh. Chỉ dùng khi học sinh yêu cầu làm bài tập/quiz, KHÔNG dùng "
        "để trả lời câu hỏi thông thường."
    )
    param_descriptions = {
        "topic_content": "Nội dung/đoạn văn bản làm cơ sở để sinh câu hỏi trắc nghiệm",
        "num_questions": "Số lượng câu hỏi cần sinh (mặc định 1)",
    }

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(self, topic_content: str, num_questions: int = 1) -> str:
        prompt = f"""Dựa trên nội dung sau, sinh ra {num_questions} câu hỏi trắc nghiệm (4 đáp án, chỉ 1 đáp án đúng).

            Nội dung:
            {topic_content}

            Chỉ trả về JSON list, KHÔNG thêm markdown code fence, KHÔNG thêm giải thích ngoài JSON, đúng format:
            [{{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer_index": 0, "explanation": "..."}}]
            """
        response = self.llm.chat([{"role": "user", "content": prompt}])
        raw = self._strip_markdown_fence(response.text)

        try:
            data = json.loads(raw)
            questions = [QuizQuestion(**q) for q in data]
            for q in questions:
                q.options = [self._clean_option(opt) for opt in q.options]
        except (json.JSONDecodeError, ValidationError, TypeError) as e:
            return f"Lỗi: không sinh được quiz hợp lệ ({e}). Thử lại với nội dung khác hoặc ít câu hỏi hơn."

        return self._format_for_observation(questions)

    @staticmethod
    def _strip_markdown_fence(text: str) -> str:
        """LLM hay tự bọc JSON trong ```json ... ``` dù đã dặn không làm vậy — dọn sạch trước khi parse."""
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        return text.strip()

    @staticmethod
    def _format_for_observation(questions: list[QuizQuestion]) -> str:
        lines = []
        for i, q in enumerate(questions, 1):
            lines.append(f"Câu {i}: {q.question}")
            for j, opt in enumerate(q.options):
                marker = "(Đáp án đúng)" if j == q.correct_answer_index else ""
                lines.append(f"  {chr(65+j)}. {opt} {marker}")
            lines.append(f"  Giải thích: {q.explanation}\n")
        return "\n".join(lines)

    @staticmethod
    def _clean_option(option: str) -> str:
        """Loại bỏ tiền tố dạng 'A. '/'B) '/'C: ' nếu model tự ý thêm vào, tránh trùng lặp
        khi format lại với ký tự đáp án ở bước sau."""
        return re.sub(r"^[A-D][\.\):]\s*", "", option.strip())