import ast
import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def strip_think_tags(text: str) -> str:
    """
    Một số model (Qwen3, DeepSeek-R1, ...) tự in chuỗi suy luận trong thẻ
    <think>...</think> trước khi ra câu trả lời thật -> loại bỏ trước khi parse JSON,
    nếu không toàn bộ phần suy luận sẽ lẫn vào và phá JSON.
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def strip_markdown_fence(text: str) -> str:
    """Loại bỏ markdown code fence (``` hoặc ```json) nếu có."""
    text = text.strip()
    pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else text


def extract_json_block(text: str) -> str:
    """
    Nếu model chèn thêm giải thích trước/sau JSON (dù đã dặn không làm vậy),
    tìm khối {...} hoặc [...] cân bằng dấu ngoặc ĐẦU TIÊN trong text.
    Model nhỏ rất hay viết kiểu: "Đây là câu hỏi: {...}" thay vì chỉ JSON thuần.
    """
    text = text.strip()
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = text.find(start_char)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return text  # không tìm thấy khối cân bằng, trả nguyên văn để bước sau tự báo lỗi rõ ràng


def parse_llm_json(text: str) -> Any:
    """
    Parse JSON từ output LLM, chịu lỗi theo nhiều lớp:
    1. Bỏ <think>...</think> nếu có
    2. Bỏ markdown code fence
    3. Trích khối JSON đầu tiên nếu model chèn giải thích quanh JSON
    4. Thử json.loads() chuẩn
    5. Fallback ast.literal_eval() nếu model dùng cú pháp Python dict (nháy đơn)
    """
    cleaned = strip_think_tags(text)
    cleaned = strip_markdown_fence(cleaned)
    cleaned = extract_json_block(cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(cleaned)
        except (ValueError, SyntaxError) as e:
            raise json.JSONDecodeError(
                f"Không parse được JSON dù đã thử fallback ast.literal_eval: {e}", cleaned, 0
            )


def parse_llm_model(text: str, model: Type[T]) -> T:
    """Parse output của LLM thành một Pydantic model."""
    data = parse_llm_json(text)
    return model(**data)
