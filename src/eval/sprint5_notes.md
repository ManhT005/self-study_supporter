# Sprint 5 Notes — Evaluation (RAG-only vs Agent+RAG)

## Trạng thái: kết quả SƠ BỘ (dùng Qwen 1.5B/1.7B do giới hạn quota Gemini)
Cần chạy lại ít nhất một phần bằng Gemini khi quota cho phép, để đối chiếu chéo trước khi đưa vào bản báo cáo chính thức. Số liệu dưới đây có giá trị tham khảo và phân tích định tính, nhưng **không nên trích dẫn như kết luận cuối cùng** của đồ án.

## Kết quả

### Bảng LLM-judge (Qwen3 1.7B làm giám khảo)

| Category | RAG-only (F / R) | Agent+RAG (F / R) | n_scored |
|---|---|---|---|
| factual | 5.0 / 5.0 | 3.57 / 4.29 | 7 |
| reasoning | 3.75 / 4.75 | 3.4 / 4.0 | 4-5 (1 parse error) |
| personalized | 5.0 / 5.0 | 2.0 / 2.5 | 4 |

### Bảng Cosine Similarity (answer vs reference_answer, bge-m3, không cần LLM)

| Category | RAG-only | Agent+RAG |
|---|---|---|
| factual | 0.87 | 0.819 |
| reasoning | 0.776 | 0.692 |
| personalized | N/A (không có reference_answer cố định) | N/A |

**2 metric độc lập (LLM-judge và cosine similarity) đồng thuận:** RAG-only nhỉnh hơn Agent+RAG ở cả factual và reasoning khi Agent dùng Qwen 1.5B.

## Diễn giải quan trọng — KHÔNG kết luận "kiến trúc Agent+RAG kém hơn"

Khoảng cách điểm số là hạn chế của **model nhỏ dùng cho Agent (Qwen 1.5B)** trong vòng lặp suy luận nhiều bước, không phải hạn chế của kiến trúc ReAct/tool-calling. Bằng chứng cụ thể thu thập xuyên suốt Sprint 3-5:
- Không tự nhận biết "đã đủ thông tin để dừng" → lặp search vô ích → hết `max_iterations` → trả lời rỗng (q009, q014, q015 timeout).
- Chọn nhầm tool: q014 chỉ cần giải thích lại nhưng Agent gọi `generate_quiz` 3 lần liên tiếp.
- Bịa số liệu dù Observation đã đúng: q003 Agent nói Unicode "21 bit" trong khi Observation ghi rõ 16 bit (RAG-only cùng retrieve, trả lời đúng).
- RAG-only chỉ cần model generate 1 lần nên ít lộ điểm yếu suy luận nhiều bước hơn — không phải vì kiến trúc RAG-only ưu việt hơn.

## Hạn chế của thiết kế eval hiện tại — cần cải thiện trước báo cáo chính thức

1. **Bộ câu personalized (q013-016) chưa đủ "chặt"** — RAG-only vẫn trả lời hợp lý dù hoàn toàn không dùng ngữ cảnh cá nhân hóa nào (chỉ nhờ retrieval tốt). Cần thiết kế lại 2-3 câu personalized bắt buộc phải biết chính xác nội dung/đáp án phiên trước mới trả lời đúng được — để phép so sánh này thực sự đo đúng giá trị của memory.
2. **Judge model (Qwen 1.7B) có năng lực gần tương đương với model được đánh giá (Qwen 1.5B)** — độ tin cậy điểm số thấp hơn nhiều so với dùng Gemini/Qwen 7B làm giám khảo. Ví dụ nghi vấn: q011, cả 2 pipeline bị chấm F=1 giống hệt nhau dù đọc thủ công thấy cả 2 câu trả lời đều hợp lý, không sai nghiêm trọng tới mức đó — cần đối chiếu lại bằng judge mạnh hơn.
3. Cosine similarity không tính được cho category personalized (không có `reference_answer` cố định) — cần metric khác cho category này (ví dụ: LLM-judge riêng tiêu chí "có tận dụng đúng ngữ cảnh trước đó hay không", chấm dạng có/không thay vì thang điểm).

## Lỗi kỹ thuật gặp phải & cách vá

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `response.text` = `None` khiến `re.search()` crash | Nghi ngờ ban đầu là Gemini safety filter, nhưng nguyên nhân thật lại nằm ở bug khác (xem dưới) | Thêm lớp phòng thủ: ép `text = response.text or ""` trong `GeminiClient`, và `if not text: return invalid` trong `parse_llm_output` |
| Agent+RAG trả lời sai hoàn toàn chủ đề (lạc sang câu hỏi trước) | `conversation_history` bị tiêm vào TẤT CẢ câu hỏi (kể cả factual/reasoning không cần), gây nhiễu ngữ cảnh — đồng thời phá vỡ tính công bằng so sánh với RAG-only (không nhận history) | Chỉ truyền `conversation_history` cho category `personalized`; đổi cách chèn từ "Observation giả" sang 1 đoạn `context_note` tách biệt rõ ràng khỏi cấu trúc ReAct |
| Agent+RAG luôn hết iteration, mất `0.0s` mỗi vòng | **Lỗi thụt lề Python** — toàn bộ logic gọi LLM/parse/xử lý action nằm ngoài vòng `while` do chỉnh sửa thủ công đoạn debug, chỉ 3 dòng đầu thực sự chạy trong loop | Kiểm tra lại indentation cẩn thận; bài học: hành vi bất thường như "0 giây" luôns là dấu hiệu code không được thực thi như tưởng, không phải lỗi logic phức tạp |
| Điểm `faithfulness=0, relevance=0` (q009) bị tính lẫn vào trung bình | Đây là mã báo lỗi parse JSON của judge, không phải điểm thật (thang điểm thật là 1-5) | `metrics.py` loại các item có `F=0 R=0` ra khỏi tính trung bình, báo cáo riêng số lượng `parse_errors` |
| Gemini quota (cả per-minute và per-day) không đủ để chạy judge cho 32 câu trả lời | Free tier hạn chế, đặc biệt quota theo ngày không thể retry | Batch nhiều câu vào 1 lời gọi LLM-judge (giảm 32 request xuống ~7); dùng `LocalEmbeddingProvider` (cosine similarity) làm metric bổ trợ miễn phí; kế hoạch dùng Qwen 7B trên Kaggle làm judge dự phòng khi cần |

## Việc còn để ngỏ trước khi hoàn thiện báo cáo
- [ ] Chạy lại toàn bộ hoặc 1 phần tiêu biểu (6-8 câu) bằng Gemini làm cả Agent LLM và judge LLM, khi quota cho phép — để có bộ đối chứng với model đủ mạnh.
- [ ] Thiết kế lại 2-3 câu personalized "chặt" hơn.
- [ ] Cân nhắc chạy Qwen 7B trên Kaggle làm judge thứ 2, đối chiếu chéo với Gemini-judge.
- [ ] Human spot-check thủ công các câu có chênh lệch điểm lớn (q003, q006, q011, q013, q014) để xác nhận độ tin cậy của judge 1.7B.
