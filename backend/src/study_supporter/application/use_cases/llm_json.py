from typing import Type
from study_supporter.ai.assessment.json_parsing import parse_llm_model, T


def chat_and_parse_model(llm, prompt: str, model: Type[T], max_retries: int = 2) -> T:
    """
    Gọi LLM, parse kết quả thành Pydantic model, TỰ ĐỘNG THỬ LẠI nếu parse thất bại.
    Đây là lớp phòng thủ quan trọng cho model nhỏ (Qwen2.5/Qwen3) — chúng thường
    không tuân thủ đúng format JSON ngay lần đầu, nhưng thường sửa được nếu được
    nhắc lại rõ ràng hơn kèm thông báo lỗi cụ thể.
    """
    last_error: Exception | None = None
    current_prompt = prompt

    for attempt in range(max_retries):
        response = llm.chat([{"role": "user", "content": current_prompt}])
        try:
            return parse_llm_model(response.text, model)
        except Exception as e:
            last_error = e
            current_prompt = (
                f"{prompt}\n\n"
                f"LƯU Ý QUAN TRỌNG: lần trả lời trước của bạn KHÔNG đúng định dạng JSON "
                f"yêu cầu (lỗi: {e}). Lần này chỉ được trả về đúng JSON hợp lệ, "
                f"KHÔNG thêm bất kỳ văn bản giải thích nào trước hoặc sau JSON."
            )

    raise last_error
