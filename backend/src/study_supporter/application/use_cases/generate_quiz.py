import re
from study_supporter.domain.assessment import QuizQuestion, QuizList


from study_supporter.application.use_cases.llm_json import chat_and_parse_model
from study_supporter.application.ports.llm import LLMAdapter


class GenerateQuizUseCase:
    name = "generate_quiz"
    description = (
        "Sinh câu hỏi trắc nghiệm dựa trên 1 đoạn nội dung cụ thể, dùng để kiểm tra "
        "kiến thức học sinh. Chỉ dùng khi học sinh yêu cầu làm bài tập/quiz, KHÔNG dùng "
        "để trả lời câu hỏi thông thường."
    )

    param_descriptions = {
        "topic_content": "Nội dung/đoạn văn bản làm cơ sở để sinh câu hỏi trắc nghiệm",
        "num_questions": "Số lượng câu hỏi cần sinh ",
    }

    def __init__(self, llm: LLMAdapter):
        self.llm = llm
        self.last_prompt: str | None = None

    def run(self, topic_content: str, num_questions: int = 1) -> str:
        prompt = f"""
    Dựa trên nội dung sau, hãy sinh ra {num_questions} câu hỏi trắc nghiệm.

    Nội dung:
    {topic_content}

    Yêu cầu:
    - Mỗi câu có đúng 4 đáp án.
    - Chỉ có 1 đáp án đúng.
    - correct_answer_index đánh số từ 0 đến 3.
    - explanation giải thích ngắn gọn đáp án đúng.

    Chỉ trả về JSON, KHÔNG thêm markdown code fence, đúng format:

    {{
    "questions": [
        {{
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "correct_answer_index": 0,
        "explanation": "..."
        }}
    ]
    }}
    """
        self.last_prompt = prompt

        try:
            quiz = chat_and_parse_model(self.llm, prompt, QuizList, max_retries=2)

            for q in quiz.questions:
                q.options = [self._clean_option(opt) for opt in q.options]

        except Exception:
            return (
                "Lỗi: không sinh được quiz hợp lệ sau nhiều lần thử. "
                "Thử lại với nội dung khác hoặc ít câu hỏi hơn."
            )

        return self._format_for_observation(quiz.questions)

    @staticmethod
    def _format_for_observation(questions: list[QuizQuestion]) -> str:
        lines = []

        for i, q in enumerate(questions, 1):
            lines.append(f"Câu {i}: {q.question}")

            for j, opt in enumerate(q.options):
                marker = "(Đáp án đúng)" if j == q.correct_answer_index else ""
                lines.append(f"  {chr(65 + j)}. {opt} {marker}")

            lines.append(f"  Giải thích: {q.explanation}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _clean_option(option: str) -> str:
        """
        Loại bỏ tiền tố như:
        A.
        B)
        C:
        D.

        để tránh hiển thị thành:
        A. A. ...
        """

        return re.sub(r"^[A-D][\.\):]\s*", "", option.strip())
