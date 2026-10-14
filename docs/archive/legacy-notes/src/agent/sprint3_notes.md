19/07/26
Sprint 3 phần lõi đã hoàn tất — ReAct loop chạy đúng: Thought → Action → Observation (tool thật, không bịa) → Thought → Final Answer, dừng đúng lúc, không rơi vào vòng lặp giả (trong trường hợp test thử)

ReAct prompting bắt buộc phải chặn LLM dừng lại ngay sau Action Input: {...} bằng stop sequence — nếu không, model (đặc biệt các model "chăm chỉ" như Gemini) có xu hướng tự hoàn thành luôn cả đoạn hội thoại tưởng tượng, bao gồm cả Observation giả

stop_sequences là bắt buộc khi tự cài ReAct loop — thiếu nó, Agent trông như hoạt động nhưng thực chất toàn bộ Observation là ảo giác của LLM.


multi-tool action: 
LLM có thể bịa toàn bộ chuỗi Action→kết quả→Final Answer trong 1 lần sinh mà không cần vi phạm stop_sequences cụ thể nào — cần parse dựa theo vị trí marker xuất hiện trước/sau trong text, không dựa theo 'có tồn tại hay không
Đây là dạng "reward hacking" tự nhiên của LLM: model học được cách "trông như đã hoàn thành nhiệm vụ" (viết Final Answer) mà không cần thực sự chờ kết quả thật — nếu không kiểm tra kỹ, đồ án sẽ trông như chạy đúng (có câu trả lời, có vẻ hợp lý) nhưng bản chất Agent không hề dùng tool thật, phá vỡ hoàn toàn ý nghĩa của kiến trúc ReAct + Tool Calling. Đây chính xác là điều khiến việc so sánh RAG-only vs Agent+RAG (đóng góp học thuật) có ý nghĩa: nếu Agent âm thầm "giả vờ" dùng tool, kết quả eval sẽ sai lệch nghiêm trọng.


# Sprint 3 Notes — Agent + Tool Calling (ReAct)

## Kết quả
ReAct loop tự viết chạy đúng end-to-end: Thought → Action → Observation (tool thật) → Thought → Final Answer. Test với 4 tool (`search_docs`, `generate_quiz`, `save_note` stub, `get_progress` stub), Agent tự chọn đúng tool theo ngữ cảnh câu hỏi.

## Kiến trúc & thuật toán tự viết

| Module | Nội dung | Ghi chú |
|---|---|---|
| `tools/base.py` | `BaseTool` — tự động sinh JSON Schema từ signature `run()` bằng `inspect` + `get_type_hints` | `safe_run()` bọc mọi lỗi tham số/nội bộ thành string, không crash chương trình khi LLM sinh sai tham số |
| `tools/search_docs.py` | Wrap lại `hybrid_search` (Sprint 1) thành tool | `param_descriptions` giúp LLM hiểu rõ ý nghĩa từng tham số, không chỉ tên biến |
| `state.py` | `AgentState` + `ScratchpadEntry` (Pydantic) — bộ nhớ làm việc trong 1 lượt hỏi-đáp | `max_iterations` chặn vòng lặp vô hạn |
| `prompt_templates.py` | System prompt ReAct chuẩn (Thought/Action/Action Input/Final Answer) | Tool description tự sinh từ `get_schema()`, luôn đồng bộ với code |
| `orchestrator.py` | Vòng lặp ReAct: gọi LLM → parse output → gọi tool thật/trả Final Answer | Parse theo **vị trí marker xuất hiện trước/sau trong text**, không theo "có tồn tại hay không" |

## Lỗi gặp phải & cách vá

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| Model deprecated (`gemini-2.5-flash` 404 "no longer available to new users") | Google rút quyền truy cập model cho project mới, sớm hơn ngày shutdown công bố | Đổi sang `gemini-3-flash-preview` (free tier hiện tại). Bài học: tên model hardcode dễ lỗi thời, cần kiểm tra định kỳ |
| LLM tự bịa toàn bộ Observation (tool giả) | Thiếu `stop_sequences`, model tự "hoàn thành" cả kịch bản Thought/Action/Observation/Final Answer trong 1 lần sinh | Thêm `stop_sequences=["Observation:"]` khi gọi `chat()` — bắt buộc với ReAct tự cài |
| LLM vẫn bịa Final Answer dù đã có stop_sequences | Model né stop sequence bằng cách không viết chữ "Observation:", tự nhảy thẳng sang bịa "đã gọi tool xong" + Final Answer trong cùng 1 response | Parse dựa theo **vị trí xuất hiện** của "Action:" so với "Final Answer:" trong text — cái nào đứng trước mới là thật, không ưu tiên "Final Answer luôn thắng" một cách mù quáng |
| `JSONDecodeError` khi parse Action Input | Model nhỏ (Qwen Ollama) hay sinh cú pháp Python dict (nháy đơn `'`) thay vì JSON chuẩn (nháy kép `"`) | Fallback `ast.literal_eval()` khi `json.loads()` thất bại — an toàn hơn `eval()` vì chỉ chấp nhận literal, không thực thi code |
| Quiz sinh ra bị trùng ký tự đáp án ("B. B. Byte") | Model tự thêm tiền tố `A./B./C.` vào trong `options`, rồi code format lại thêm 1 lớp nữa | Regex `_clean_option()` loại bỏ tiền tố cũ trước khi format |

## Quan sát định tính: Gemini vs Ollama (Qwen 1.5B)
- Gemini tuân thủ format ReAct tốt hơn nhiều, hiếm khi bịa Observation sau khi có stop_sequences.
- Qwen 1.5B (model nhỏ, chỉ dùng để test logic — bản 7B thật dùng ở Sprint 5) có 2 hạn chế rõ rệt:
  - Không tự nhận biết "đã đủ thông tin để dừng" — có thể lặp lại search nhiều lần dù Observation đầu tiên đã đủ trả lời, dẫn đến hết `max_iterations` mà chưa ra Final Answer.
  - Đôi khi không giữ nguyên kết quả tool thật trong Final Answer, tự viết lại nội dung khác (ví dụ tự đổi đáp án quiz).
- Đây là dữ liệu định tính quan trọng cho Sprint 5 (so sánh RAG-only vs Agent+RAG, và gián tiếp cho thấy chất lượng LLM ảnh hưởng lớn đến hiệu quả ReAct).

## Quyết định kiến trúc quan trọng
- Interface `LLMAdapter`/`ChatResponse` (Sprint 2) đã đủ tổng quát để `orchestrator.py` không cần biết đang chạy Gemini hay Ollama — chỉ cần thêm `stop_sequences` vào signature `chat()`.
- `orchestrator.py` nhận `tools: list[BaseTool]` tổng quát — thêm/bớt tool không cần sửa logic vòng lặp, chỉ cần tool mới kế thừa đúng `BaseTool`.

## Việc còn để ngỏ (không chặn Sprint 4)
- `max_iterations` mặc định (5) đôi khi hơi thấp với model nhỏ hay "trượt" — cân nhắc tăng lên 7-8 khi test với Ollama.
- Chưa benchmark định lượng số iteration trung bình, tỷ lệ Agent chọn đúng tool — để dành đo chính thức ở Sprint 5.