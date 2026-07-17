# TÀI LIỆU THIẾT KẾ & KẾ HOẠCH TRIỂN KHAI DỰ ÁN: AI STUDY AGENT

**Vị trí định hướng:** AI Agent & Algorithm (Chương trình Sinh viên Công nghệ Tập sự)
**Kiến trúc:** Functional UI / Workspace-Centric (No-Framework Agent)
**Team:** 4 thành viên · **Thời lượng:** 6 sprint

> **Ghi chú phiên bản:** Tài liệu này là bản hợp nhất giữa thiết kế kỹ thuật gốc và bản mockup kiến trúc (`system_overview.html`). Các điểm mâu thuẫn giữa hai bản (embedding model, chiến lược chunking, retrieval, folder structure) đã được chốt lại ở đây — đây là **nguồn thiết kế duy nhất (single source of truth)** từ nay về sau.

---

## 1. TỔNG QUAN DỰ ÁN (EXECUTIVE SUMMARY)

Dự án **AI Study Agent** là một hệ thống hỗ trợ học tập cá nhân hóa thế hệ mới. Khác biệt với các Chatbot RAG (Retrieval-Augmented Generation) truyền thống vốn thụ động và dựa vào văn bản tự do, hệ thống này được thiết kế theo mô hình **Functional UI (Giao diện chức năng)**.

Hệ thống đóng vai trò như một **Agent tự chủ (Autonomous Agent)**: tự phân tích tài liệu học tập, tự động kiến tạo bản đồ tri thức (Knowledge Graph) ở mức rút gọn, tự định hướng công cụ (Tool Calling) thông qua vòng lặp suy luận ReAct, và chủ động thiết kế bài tập cá nhân hóa dựa trên điểm yếu của người học.

### Đóng góp học thuật (Academic Contribution)

Đây là phần **quan trọng nhất về mặt báo cáo khoa học** — cần được thiết kế chặt chẽ ngay từ đầu, không phải chỉ là tính năng phụ:

- **Câu hỏi nghiên cứu:** Agent+RAG (có tool calling, có memory, có ReAct loop) có cải thiện chất lượng hỗ trợ học tập so với RAG-only (retrieve-then-generate thuần túy) hay không, và cải thiện ở khía cạnh nào?
- **Phương pháp:**
  1. Xây dựng bộ **eval_dataset.json** (~50 câu hỏi) trên cùng một bộ tài liệu học tập, chia theo loại: factual (tra cứu trực tiếp), reasoning (suy luận nhiều bước), personalized (cần nhớ ngữ cảnh phiên trước).
  2. Chạy cùng một bộ câu hỏi qua 2 pipeline: **RAG-only** (retrieve top-k → generate) và **Agent+RAG** (đầy đủ ReAct + tool + memory), **cùng LLM, cùng retriever, cùng context window** để đảm bảo so sánh công bằng (kiểm soát biến nhiễu).
  3. Chấm điểm bằng **LLM-as-judge** (Qwen2.5-7B qua Ollama, chạy batch trên Kaggle GPU để không bị giới hạn rate limit) theo 3 tiêu chí độc lập: _faithfulness_ (không bịa đặt ngoài tài liệu), _relevance_ (đúng trọng tâm câu hỏi), _personalization_ (có tận dụng ngữ cảnh học tập trước đó hay không — tiêu chí này chỉ Agent+RAG mới có thể đạt cao).
  4. Bổ sung **user study nhỏ** (5–10 sinh viên thật dùng thử) để đối chiếu điểm LLM-judge với cảm nhận thực tế — tăng độ tin cậy học thuật so với chỉ dùng LLM-as-judge đơn thuần.
- **Rủi ro cần lường trước:** LLM-as-judge có thể thiên vị câu trả lời dài/có structure — nên cố định prompt chấm điểm, và báo cáo cả inter-rater agreement giữa LLM-judge và user study.

---

## 2. ĐỊNH HƯỚNG CÔNG NGHỆ (TECHNICAL STACK)

| Phân tầng               | Công nghệ lựa chọn                                                                                                                                                                                                                           | Lý do & Vai trò thuật toán                                                                                                                                                                                            |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **UI Layer**            | Streamlit                                                                                                                                                                                                                                    | Xây dựng giao diện Workspace 3 cột nhanh chóng, quản lý trạng thái động (State-driven UI).                                                                                                                            |
| **Orchestration**       | Python thuần (Pure Python) + Gemini SDK                                                                                                                                                                                                      | Tự cài đặt vòng lặp ReAct, không phụ thuộc framework bên thứ ba (LangChain/LangGraph) để tối ưu kiểm soát và chứng minh năng lực thuật toán.                                                                          |
| **Embedding**           | **Gemini Embedding API** (`text-embedding-004`, free tier) cho dev/demo; **`sentence-transformers` (bge-m3, chạy local/Kaggle)** cho batch re-embed và eval                                                                                  | _Đã sửa so với bản nháp trước:_ bản mockup cũ dùng OpenAI `text-embedding-3-small`, là dịch vụ trả phí — vi phạm ràng buộc ngân sách 0đ. bge-m3 hỗ trợ tiếng Việt tốt và chạy được trên GTX 3050 4GB hoặc Kaggle GPU. |
| **Chunking**            | **Semantic Chunking tự cài đặt**: gộp câu liền kề theo ngưỡng cosine similarity giữa embedding câu (sentence-window breakpoint detection); fallback về fixed-size 512 token/overlap 100 nếu văn bản không tách câu rõ ràng (bảng, công thức) | Semantic chunking giữ được ranh giới ý nghĩa tốt hơn fixed-size thuần túy, đồng thời vẫn là thuật toán tự viết (không dùng thư viện chunking có sẵn) — phù hợp tiêu chí "chứng minh năng lực thuật toán".             |
| **RAG & Search Engine** | ChromaDB (dense) + Rank-BM25 (sparse), trộn kết quả bằng **Reciprocal Rank Fusion (RRF)**                                                                                                                                                    | Hybrid Search giải quyết điểm yếu của dense-only: bỏ sót từ khóa chính xác (mã môn học, thuật ngữ riêng, số liệu). RRF là thuật toán fusion đơn giản, dễ tự cài, dễ giải thích trong báo cáo.                         |
| **Graph Processing**    | NetworkX — **giữ lại**, xem mục 3 để biết lý do và phạm vi cụ thể                                                                                                                                                                            | Xử lý cấu trúc đồ thị khái niệm, phát hiện chu trình (cycle) và sắp xếp lộ trình học bằng Topological Sort.                                                                                                           |
| **Agent Reasoning**     | ReAct loop thuần Python, tối đa 5 iteration/lượt, có log Thought/Action/Observation                                                                                                                                                          | Minh bạch quá trình suy luận — vừa phục vụ debug, vừa là UI feature (Agent Thought Log) tăng tính "explainable" cho báo cáo.                                                                                          |
| **Database & Memory**   | SQLite + SQLAlchemy (ORM) cho tiến độ học tập; ChromaDB collection riêng cho bộ nhớ dài hạn                                                                                                                                                  | Tách bạch dữ liệu có cấu trúc (điểm quiz, timestamp) khỏi dữ liệu ngữ nghĩa tự do (ghi chú học tập).                                                                                                                  |
| **Validation Layer**    | Pydantic V2                                                                                                                                                                                                                                  | Định nghĩa chặt chẽ schema đầu ra (Structured Outputs) cho mọi tool — ví dụ `QuizQuestion`, `GraphNode`, `ToolCallResult` — phục vụ hiển thị UI và giao tiếp giữa các module mà không cần parse JSON thủ công.        |
| **LLM**                 | Gemini 1.5 Flash (free, 15 req/phút) cho dev/demo trực tiếp; Ollama + Qwen2.5-7B trên Kaggle GPU cho batch eval không giới hạn                                                                                                               | LLMAdapter interface trừu tượng (`chat`, `stream`, `call_with_tools`) giúp swap 2 model không đổi code gọi.                                                                                                           |
| **Deployment**          | Docker + Hugging Face Spaces                                                                                                                                                                                                                 | Đóng gói môi trường nhất quán, phân phối sản phẩm demo thực tế cho hội đồng truy cập từ xa.                                                                                                                           |

---

## 3. QUYẾT ĐỊNH: GIỮ LẠI KNOWLEDGE GRAPH LAYER

Sau khi cân nhắc, **nên giữ lại** vì nó không chỉ là tính năng trang trí mà đóng vai trò thực trong vận hành hệ thống:

- **Định tuyến lộ trình học:** Sau khi parse tài liệu, Agent dùng LLM để rút trích danh sách khái niệm + quan hệ tiên quyết (concept → prerequisite) ở mức tiêu đề/mục lục tài liệu (không cần phân tích toàn văn sâu). NetworkX build đồ thị có hướng từ đó, chạy **Topological Sort** để đề xuất thứ tự học hợp lý, và **Cycle Detection** để cảnh báo nếu LLM rút trích ra quan hệ vòng lặp phi logic (chính là một cơ chế tự kiểm tra chất lượng output của LLM — điểm cộng học thuật).
- **Cá nhân hóa quiz:** `generate_quiz` tool có thể dùng đồ thị để ưu tiên sinh câu hỏi cho các node "gốc" (khái niệm nền tảng) trước khi sang node phụ thuộc, thay vì chọn ngẫu nhiên.
- **Giá trị UI thực tế:** đúng như định hướng "bản đồ lộ trình học tương tác" đã có trong bản mockup — sinh viên nhìn thấy được cấu trúc môn học, không chỉ chat tuyến tính.

**Phạm vi rút gọn để khả thi với team 2 người:**

- Đồ thị được xây **một lần khi upload tài liệu**, không cập nhật real-time.
- Rút trích khái niệm bằng 1 lời gọi LLM có structured output (Pydantic schema `GraphNode`/`GraphEdge`), không cần NLP pipeline riêng.
- Không làm graph editing UI phức tạp — chỉ hiển thị đọc (read-only) dạng cây/danh sách thứ tự đã sort.

---

## 4. PHÂN LOẠI TÍNH NĂNG: MUST-HAVE vs NICE-TO-HAVE

Với 2 người và 6 sprint, cần rõ ràng đâu là lõi bắt buộc để bảo vệ luận điểm khoa học, đâu là mở rộng chỉ làm nếu còn thời gian:

| Ưu tiên         | Tính năng                                                                   | Lý do                                                                                       |
| :-------------- | :-------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| 🔴 Must-have    | RAG pipeline (parse → chunk → embed → hybrid retrieve)                      | Nền tảng, không có thì không có gì để so sánh                                               |
| 🔴 Must-have    | ReAct Agent + 4 tools (search_docs, generate_quiz, save_note, get_progress) | Đối tượng nghiên cứu chính (Agent+RAG)                                                      |
| 🔴 Must-have    | Memory 2 tầng (short-term + long-term)                                      | Cần thiết để đo tiêu chí "personalization" trong eval                                       |
| 🔴 Must-have    | Eval framework (RAG-only vs Agent+RAG, LLM-as-judge)                        | Đây chính là đóng góp khoa học của đồ án                                                    |
| 🟡 Nice-to-have | Knowledge Graph (bản rút gọn ở mục 3)                                       | Tăng chiều sâu thuật toán, nhưng có thể cắt nếu sprint 4–5 bị chậm                          |
| 🟡 Nice-to-have | Hybrid Search (BM25 + RRF)                                                  | Có thể tạm dùng dense-only nếu thiếu thời gian, ghi rõ là "future work" trong báo cáo       |
| 🟢 Optional     | Docker + HF Spaces public deploy                                            | Tốt cho demo nhưng không ảnh hưởng luận điểm khoa học — có thể demo local nếu hết thời gian |
| 🟢 Optional     | User study định tính                                                        | Tăng độ tin cậy eval nhưng có thể lược bớt nếu không đủ người tham gia thử nghiệm           |

---

## 5. CẤU TRÚC THƯ MỤC HỆ THỐNG (FOLDER STRUCTURE)

```
ai-study-agent/
├── .env                          # API Keys (GEMINI_API_KEY) — KHÔNG commit
├── .env.example                  # Template — commit
├── README.md
├── requirements.txt
├── app.py                        # Entry point Streamlit
│
├── src/
│   ├── __init__.py
│   ├── config.py                 # Hằng số hệ thống, đọc .env
│   │
│   ├── rag/                      # Sprint 1 — RAG pipeline
│   │   ├── pdf_parser.py         # PyMuPDF: PDF/DOCX → text + metadata
│   │   ├── chunker.py            # Semantic chunking (sentence-window breakpoint)
│   │   ├── embedder.py           # Gemini Embedding API + bge-m3 local fallback
│   │   ├── vector_store.py       # ChromaDB wrapper: 2 collection (documents, user_memory)
│   │   ├── bm25_index.py         # Sparse index song song với dense
│   │   └── hybrid_retriever.py   # RRF fusion dense + sparse
│   │
│   ├── llm/                      # Sprint 2 — LLM integration
│   │   ├── llm_adapter.py        # Abstract interface: chat(), stream(), call_with_tools()
│   │   ├── gemini_client.py
│   │   └── ollama_client.py
│   │
│   ├── agent/                    # Sprint 3 — Agent + tools
│   │   ├── orchestrator.py       # ReAct while-loop, max 5 iteration, có logging
│   │   ├── state.py              # AgentState (Pydantic)
│   │   ├── prompt_templates.py
│   │   └── tools/
│   │       ├── base.py           # Base class tự trích JSON Schema cho tool
│   │       ├── search_docs.py
│   │       ├── generate_quiz.py
│   │       ├── save_note.py
│   │       └── get_progress.py
│   │
│   ├── graph/                    # Sprint 4 — Knowledge Graph (rút gọn, xem mục 3)
│   │   ├── graph_builder.py      # LLM rút trích concept + prerequisite → NetworkX DiGraph
│   │   ├── graph_algorithms.py   # Topological Sort, Cycle Detection
│   │   └── schemas.py            # Pydantic: GraphNode, GraphEdge
│   │
│   ├── memory/                   # Sprint 4 — Memory system
│   │   ├── short_term.py         # Conversation history trong session
│   │   ├── long_term.py          # ChromaDB collection "user_memory"
│   │   └── progress_db.py        # SQLite + SQLAlchemy: lịch sử quiz
│   │
│   └── eval/                     # Sprint 5 — Evaluation (đóng góp học thuật)
│       ├── eval_runner.py        # Chạy cả 2 pipeline (RAG-only, Agent+RAG) trên eval_dataset
│       ├── llm_judge.py          # Chấm điểm: faithfulness, relevance, personalization
│       └── metrics.py            # Tổng hợp, xuất CSV/bảng so sánh
│
├── ui/                            # Sprint 6 — Workspace-Centric UI
│   ├── dashboard.py               # Điều phối giao diện 3 cột
│   └── components/
│       ├── sidebar.py             # Upload file & Agent Thought Log
│       ├── graph_viewer.py        # Cột giữa: lộ trình học (đọc, không edit)
│       └── quiz_arena.py          # Cột phải: quiz & đánh giá
│
├── data/
│   ├── demo_docs/                 # PDF demo, commit vào repo
│   ├── chroma_db/                 # ChromaDB persistent (gitignore)
│   └── eval_dataset.json          # ~50 câu hỏi eval, có nhãn loại + ground truth
│
└── tests/
    ├── test_agent.py              # Kiểm thử ReAct loop
    ├── test_graph.py              # Kiểm thử cycle detection / topo sort
    └── eval_rag.py                # Đánh giá RAG tự động (LLM-as-judge)
```

---

## 6. RỦI RO KỸ THUẬT CẦN XỬ LÝ TRƯỚC DEMO

Đây là các lỗ hổng dễ bị hội đồng bắt lỗi hoặc gây sự cố ngay trong buổi bảo vệ — cần xử lý sớm, không để đến sprint cuối:

| Rủi ro                                                                          | Giải pháp                                                                                                                                                                                                           |
| :------------------------------------------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Gemini free tier giới hạn 15 req/phút → dễ lỗi 429 khi demo trực tiếp           | Cài retry với exponential backoff trong `gemini_client.py`; nếu vẫn fail, tự động fallback sang `ollama_client.py` (nhờ có sẵn LLM Adapter interface, việc swap gần như miễn phí về công sức).                      |
| SQLite không thread-safe mặc định, Streamlit có thể chạy đa luồng               | Dùng SQLAlchemy session theo scoped session, hoặc `check_same_thread=False` + serialize ghi bằng lock đơn giản.                                                                                                     |
| RAG có thể trích dẫn sai nguồn hoặc bịa nội dung ngoài tài liệu (hallucination) | Thêm bước verify nhẹ: sau khi generate, kiểm tra câu trả lời có overlap từ khóa/embedding với đúng chunk đã trích dẫn hay không; nếu overlap quá thấp, gắn cảnh báo "chưa chắc chắn" thay vì hiển thị citation sai. |
| Nhiều người dùng thử cùng lúc trong buổi demo có thể lẫn dữ liệu                | Không cần auth phức tạp — sinh `user_id` ngẫu nhiên lưu trong `st.session_state` ngay khi mở app, dùng để filter collection ChromaDB và bảng SQLite.                                                                |
| LLM-as-judge có thể thiên vị câu trả lời dài                                    | Cố định prompt chấm điểm, giới hạn độ dài câu trả lời khi eval, và đối chiếu với user study nhỏ (mục 1) để kiểm tra độ lệch.                                                                                        |

---

## 7. KẾ HOẠCH 6 SPRINT

| Sprint | Trọng tâm kiến thức      | Deliverable chính                                                                                |
| :----- | :----------------------- | :----------------------------------------------------------------------------------------------- |
| 1      | RAG cơ bản               | `rag/` hoàn chỉnh: parse → chunk → embed → hybrid retrieve, test bằng vài câu hỏi thủ công       |
| 2      | LLM Integration          | `llm/` hoàn chỉnh: Gemini + Ollama qua cùng interface, benchmark tốc độ/chất lượng 2 model       |
| 3      | Agent + Tool Calling     | `agent/` hoàn chỉnh: ReAct loop + 4 tools, có Thought Log log ra console/UI                      |
| 4      | Knowledge Graph + Memory | `graph/` + `memory/`: đồ thị lộ trình học + memory 2 tầng hoạt động cùng agent                   |
| 5      | Evaluation               | `eval/` hoàn chỉnh: chạy so sánh RAG-only vs Agent+RAG trên `eval_dataset.json`, có bảng kết quả |
| 6      | UI + Đóng gói + Báo cáo  | `ui/` hoàn chỉnh, Docker + demo trên HF Spaces (nếu kịp), viết báo cáo khoa học từ kết quả eval  |

---

_Hết tài liệu._
