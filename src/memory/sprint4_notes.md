# Sprint 4 Notes — Knowledge Graph (rút gọn) + Memory System

## Kết quả
Concept Graph rút trích từ tài liệu (7-8 node, 7 edge), Topological Sort cho ra thứ tự học hợp lý, không có cycle. Memory 2 tầng (short-term RAM + long-term ChromaDB) và SQLite progress tracking hoạt động đúng, có user isolation. Thay thành công 2 tool stub (`save_note`, `get_progress`) bằng bản thật mà **không cần sửa `orchestrator.py`** — xác nhận giá trị thực tế của kiến trúc `BaseTool` tổng quát từ Sprint 3.

## Kiến trúc & thuật toán tự viết

| Module | Nội dung | Ghi chú |
|---|---|---|
| `graph/schemas.py` | `GraphNode`, `GraphEdge`, `ConceptGraph` (Pydantic) | Edge có hướng `source -> target` = "học source trước target" |
| `graph/graph_builder.py` | 1 lời gọi LLM rút trích khái niệm + quan hệ tiên quyết từ vài chunk đầu tài liệu | Nếu extraction thất bại, trả về graph rỗng — không làm hỏng pipeline upload (graph là nice-to-have, không phải phụ thuộc cứng) |
| `graph/graph_algorithms.py` | `detect_cycles` (NetworkX `simple_cycles`), `suggest_learning_path` (`topological_sort`) | `to_networkx()` convert Pydantic model sang `nx.DiGraph` để chạy thuật toán |
| `llm/json_utils.py` | `strip_markdown_fence`, `parse_llm_json`, `parse_llm_model` (generic, dùng `TypeVar`) | Dùng chung cho mọi tính năng cần "LLM sinh JSON → validate Pydantic" (graph, và các tính năng tương lai) |
| `memory/short_term.py` | `ShortTermMemory` — lịch sử hội thoại trong RAM, giới hạn `max_turns` | Không persist, mất khi tắt app — đúng bản chất "working memory" |
| `memory/long_term.py` | `LongTermMemory` — ghi chú lưu vào ChromaDB collection `user_memory` | Cách nhau hoàn toàn với collection `documents`; filter `where={"user_id": ...}` đảm bảo user isolation |
| `memory/progress_db.py` | `ProgressDB` (SQLAlchemy) — lưu lịch sử làm quiz, tính accuracy theo user | `check_same_thread=False` xử lý sẵn rủi ro Streamlit đa luồng đã note từ thiết kế ban đầu |

## Lỗi/vấn đề gặp phải & cách xử lý

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `parse_llm_json(response)` lỗi | Truyền nhầm `ChatResponse` object thay vì `response.text` | Luôn lấy `.text` trước khi parse JSON — lưu ý interface `ChatResponse` không phải string thô |
| Chiều edge đôi khi hơi ngược logic (`ma_hoa -> du_lieu`) | LLM chỉ được cho xem vài chunk đầu, thiếu ngữ cảnh toàn tài liệu để suy luận đúng thứ tự | Chấp nhận được ở mức rút gọn Sprint 4 — không ảnh hưởng tính đúng đắn của thuật toán Topological Sort/Cycle Detection, chỉ ảnh hưởng chất lượng dữ liệu đầu vào |

## Quyết định kiến trúc quan trọng
- **Không refactor `generate_quiz.py` (Sprint 3) sang dùng `parse_llm_model` chung** — dù cùng nhu cầu parse JSON, đổi format quiz (list trần → `{"questions": [...]}`) đòi hỏi sửa cả prompt lẫn format Observation của 1 tool đã chạy ổn định. Quyết định: chỉ áp dụng `json_utils.py` cho tính năng **mới** từ Sprint 4 trở đi, không phá vỡ code cũ đang hoạt động tốt để đổi lấy sự nhất quán thuần lý thuyết.
- **Graph xây 1 lần lúc upload, không real-time update** — đúng phạm vi đã chốt từ đầu, giữ Sprint 4 khả thi với team 2 người.
- **2 tool memory không cần sửa `orchestrator.py` khi chuyển từ stub sang thật** — xác nhận lợi ích thực tế của Dependency Inversion: `BaseTool` interface ổn định, chỉ đổi implementation bên trong.

## Việc còn để ngỏ (không chặn Sprint 5)
- Chưa có cơ chế tự động gắn `user_id` vào câu hỏi của học sinh — hiện phải nói rõ trong câu hỏi test (ví dụ "tiến độ của user_001"). Sprint 6 (UI) sẽ dùng `st.session_state` để tự động gắn, không cần sửa tool.
- Chưa test graph với toàn bộ tài liệu dài (mới test 5 chunk đầu) — cân nhắc giới hạn số ký tự đưa vào prompt graph extraction để tránh vượt context/tốn token khi tài liệu dài hơn.
- `ShortTermMemory` chưa được nối vào `orchestrator.py` (Agent hiện tại không dùng lịch sử hội thoại đa lượt) — để dành tích hợp khi làm UI Streamlit (Sprint 6), khi đó mỗi câu hỏi mới sẽ đi kèm lịch sử ngắn hạn của phiên.