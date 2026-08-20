# KẾ HOẠCH: MỞ RỘNG ĐA NHÀ CUNG CẤP LLM (MULTI-PROVIDER FREE CREDIT POOL)

## 1. Mục tiêu

Tăng tổng hạn mức sử dụng LLM khả dụng cho hệ thống bằng cách **xoay vòng nhiều nhà cung cấp miễn phí** thay vì phụ thuộc duy nhất vào Gemini, tận dụng kiến trúc `LLMAdapter` (Dependency Inversion) đã có sẵn từ Sprint 2 — không cần sửa `orchestrator.py` hay bất kỳ tool nào.

## 2. Hiện trạng

- Chỉ có 2 provider: Gemini (chính, hạn mức chặt nhất) và Ollama cục bộ (dự phòng, chậm hơn, chất lượng thấp hơn với model nhỏ).
- Cơ chế dự phòng hiện tại (`_run_with_fallback` trong `chat.py`) là **nhị phân, cứng**: chỉ biết chuyển Gemini → Ollama, không mở rộng được sang provider thứ 3 trở lên mà không sửa code.

## 3. Danh sách nhà cung cấp đề xuất

> ⚠️ Hạn mức miễn phí thay đổi thường xuyên theo chính sách nhà cung cấp — **bắt buộc kiểm tra lại trực tiếp trên trang chính thức của từng provider trước khi triển khai**, số liệu dưới đây chỉ mang tính tham khảo tại thời điểm lập kế hoạch.

| Ưu tiên | Provider | Đặc điểm | Endpoint | Cần thẻ tín dụng? |
|---|---|---|---|---|
| 1 | **Gemini** (đã có) | Chất lượng cao nhất, hạn mức chặt | SDK riêng (đã tích hợp) | Không |
| 2 | **Groq** | Tốc độ rất nhanh (chip LPU), RPM/RPD khá | Tương thích OpenAI | Không |
| 3 | **Cerebras** | Khối lượng token/ngày lớn | Tương thích OpenAI | Không |
| 4 | **GitHub Models** | Sinh viên có sẵn tài khoản GitHub, nhiều model | Tương thích OpenAI | Không (cần tài khoản GitHub) |
| 5 | **OpenRouter (model :free)** | Tổng hợp nhiều model mở, dự phòng thêm | Tương thích OpenAI | Không |
| — | **Mistral (Experiment tier)** | Trần token/tháng rất cao nhưng RPM cực thấp (~2) | Tương thích OpenAI | Không |
| Cuối cùng | **Ollama cục bộ** (đã có) | Không giới hạn, luôn khả dụng, chậm nhất | HTTP local | Không |

**Ghi chú xếp Mistral riêng:** RPM quá thấp không phù hợp cho vòng lặp ReAct tương tác (mỗi câu hỏi cần 2-5 lời gọi LLM liên tiếp, chờ ~30s/lời gọi là không chấp nhận được cho chat trực tiếp) — chỉ nên dùng cho tác vụ chạy nền không cần phản hồi tức thời (ví dụ batch eval ở Sprint 5), không đưa vào vòng xoay chính của chat.

## 4. Kiến trúc kỹ thuật

### 4.1 Giảm chi phí triển khai bằng 1 class dùng chung

Vì Groq, Cerebras, GitHub Models, OpenRouter đều expose endpoint tương thích chuẩn `chat completions` của OpenAI, chỉ cần **1 class mới** thay vì viết riêng cho từng provider:

```python
# src/llm/openai_compatible_client.py
class OpenAICompatibleClient(LLMAdapter):
    def __init__(self, base_url: str, api_key: str, model: str,
                 max_retries: int = 3, max_calls: int = 20, period: float = 60.0):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(max_calls=max_calls, period=period)

    def chat(self, messages, system_prompt=None, stop_sequences=None) -> ChatResponse:
        # gọi POST {base_url}/chat/completions theo chuẩn OpenAI,
        # parse response.choices[0].message.content -> ChatResponse
        ...
```

Khởi tạo cho từng provider chỉ khác `base_url`/`api_key`/`model`:

```python
groq_client = OpenAICompatibleClient(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",  # xác nhận lại tên model hiện hành trước khi dùng
)
```

### 4.2 `MultiProviderLLM` — điều phối xoay vòng

```python
class MultiProviderLLM(LLMAdapter):
    def __init__(self, providers: list[LLMAdapter]):
        self.providers = providers          # thứ tự ưu tiên giảm dần
        self.dead_until_tomorrow: set[int] = set()

    def chat(self, messages, system_prompt=None, stop_sequences=None) -> ChatResponse:
        last_error = None
        for i, provider in enumerate(self.providers):
            if i in self.dead_until_tomorrow:
                continue
            try:
                return provider.chat(messages, system_prompt, stop_sequences)
            except RuntimeError as e:          # quy ước: quota theo NGÀY
                self.dead_until_tomorrow.add(i)
                last_error = e
                continue
            except ClientErrorLike as e:       # quota theo PHÚT -> thử provider kế tiếp NGAY
                last_error = e
                continue
        raise RuntimeError(f"Tất cả provider đều hết quota hôm nay. Lỗi cuối: {last_error}")
```

**Nguyên tắc điều phối:** lỗi quota-theo-phút → thử ngay provider tiếp theo (không `sleep`, tối đa hóa throughput tức thời). Lỗi quota-theo-ngày → đánh dấu "chết" tới hết ngày, bỏ qua hẳn trong các lượt gọi sau (tránh lãng phí thời gian thử lại vô ích).

### 4.3 Tương thích ngược hoàn toàn

`MultiProviderLLM` **implement `LLMAdapter`** giống hệt `GeminiClient`/`OllamaClient` — truyền thẳng vào `ReActOrchestrator(llm=multi_provider_llm, tools=...)` mà không cần sửa 1 dòng nào trong `orchestrator.py`, `chat.py`, hay bất kỳ tool nào.

## 5. Kế hoạch triển khai theo checkpoint

| Checkpoint | Nội dung | Ước lượng |
|---|---|---|
| **CP1** | Đăng ký API key Groq + Cerebras + GitHub Models (miễn phí, không thẻ), lưu vào `.env` | ~15 phút |
| **CP2** | Viết `OpenAICompatibleClient`, test độc lập với từng provider (1 câu hỏi đơn giản/provider) | ~30-45 phút |
| **CP3** | Viết `MultiProviderLLM`, test giả lập lỗi quota (mock exception) để xác nhận đúng logic chuyển provider | ~30 phút |
| **CP4** | Thay `llm = _get_llm_client()` trong `sidebar.py` bằng `llm = _build_multi_provider_llm()`, giữ nguyên lựa chọn Gemini/Ollama chủ động ở UI làm 2 provider đầu/cuối trong danh sách | ~20 phút |
| **CP5** | Test thực tế: cố tình gọi liên tục cho tới khi 1 provider báo quota, xác nhận hệ thống tự chuyển sang provider kế tiếp mà không gián đoạn chat | ~30 phút (phụ thuộc tốc độ hết quota thật) |

## 6. Rủi ro và cách giảm thiểu

| Rủi ro | Cách giảm thiểu |
|---|---|
| Chất lượng câu trả lời không đồng đều giữa các provider (model khác nhau) | Xếp thứ tự ưu tiên theo chất lượng giảm dần (Gemini trước, model nhỏ hơn sau); ghi log provider nào đã trả lời để phân tích sau nếu cần |
| Tên model/endpoint của provider thay đổi theo thời gian | Đưa tên model vào biến môi trường, không hardcode; kiểm tra lại trước mỗi lần demo quan trọng |
| Độ trễ tăng khi phải thử nhiều provider trước khi thành công | Giới hạn `max_retries` hợp lý ở tầng `MultiProviderLLM`, không thử tất cả N provider cho 1 request nếu N lớn |
| Rò rỉ API key nếu commit nhầm `.env` | Đã có `.gitignore` chặn `.env` từ Sprint 1, không cần thêm |

## 7. Tiêu chí hoàn thành

- Hệ thống có ít nhất 3 provider LLM tương tác được (Gemini + 2 provider mới) ngoài Ollama.
- Khi 1 provider bất kỳ báo lỗi quota (mô phỏng hoặc thật), chat tiếp tục hoạt động bình thường qua provider kế tiếp, người dùng không thấy gián đoạn ngoài 1 dòng cảnh báo (nếu có).
- Không có thay đổi nào trong `orchestrator.py`/tool — xác nhận đúng giá trị của kiến trúc `LLMAdapter` đã thiết kế từ đầu.

---
