import re


def parse_quiz_from_text(text: str, topic_label: str = "Chủ đề chung") -> list[dict] | None:
    """Parse quiz từ output của Agent thành danh sách câu hỏi."""
    blocks = re.findall(
        r"^Câu\s*\d+:\s*(.*?)(?=^Câu\s*\d+:|\Z)", text, flags=re.MULTILINE | re.DOTALL
    )
    if not blocks:
        return None

    questions = []
    for block in blocks:
        block = block.strip()

        # Tách "Giải thích:" ra TRƯỚC khi tìm option — nếu không, đáp án cuối
        # cùng (D) sẽ nuốt luôn cả phần giải thích vào trong text của nó, vì
        # lookahead của regex option chỉ dừng khi gặp đáp án A-D tiếp theo
        # hoặc hết chuỗi, mà dòng "Giải thích:" không khớp cả 2 điều kiện đó.
        explanation_match = re.search(
            r"^\s*Giải thích:\s*(.+)", block, flags=re.MULTILINE | re.DOTALL
        )
        if explanation_match:
            options_zone = block[: explanation_match.start()]
            explanation = explanation_match.group(1).strip()
        else:
            options_zone = block
            explanation = ""

        question_match = re.search(r"^(.*?\?)", options_zone.strip(), re.DOTALL)
        options = re.findall(
            r"^\s*[A-D]\.\s*(.+?)(?=\n\s*[A-D]\.\s*|\Z)",
            options_zone,
            flags=re.MULTILINE | re.DOTALL,
        )

        labels = re.findall(r"^\s*([A-Z])\.\s*", options_zone, flags=re.MULTILINE)
        if not question_match or len(options) != 4 or labels != list("ABCD"):
            return None

        marker = r"\(\s*(?:đáp án đúng|correct(?: answer)?)\s*\)"
        counts = [len(re.findall(marker, opt, flags=re.IGNORECASE)) for opt in options]
        if sum(counts) != 1:
            return None
        correct_index = next(i for i, count in enumerate(counts) if count == 1)
        cleaned_options = [re.sub(marker, "", opt, flags=re.IGNORECASE).strip() for opt in options]
        if any(not option for option in cleaned_options):
            return None

        questions.append(
            {
                "question": question_match.group(1).strip(),
                "options": cleaned_options,
                "correct_index": correct_index,
                "explanation": explanation,
                "topic": topic_label,
            }
        )

    return questions
