# 🎓 AI Study Agent

> **AI Study Agent** là một hệ thống hỗ trợ học tập cá nhân hóa thế hệ mới. Khác biệt với các Chatbot RAG truyền thống vốn thụ động, hệ thống này đóng vai trò như một **Agent tự chủ (Autonomous Agent)**: tự phân tích tài liệu, kiến tạo bản đồ tri thức, chủ động tra cứu thông tin (Tool Calling / ReAct), và thiết kế bài tập kiểm tra cá nhân hóa dựa trên điểm yếu của người học.

---

## ✨ Tính năng nổi bật

- **📄 Document Processing & Hybrid RAG:**
  - Hỗ trợ phân tích đa dạng tài liệu học tập (PDF, DOCX) với **PyMuPDF**.
  - **Semantic Chunking:** Cắt đoạn thông minh dựa trên ngữ nghĩa (cosine similarity của các câu).
  - **Hybrid Search (RRF):** Kết hợp tìm kiếm vector (Dense - ChromaDB) và từ khóa (Sparse - BM25) giúp truy xuất chính xác cả khái niệm rộng lẫn mã môn học, thuật ngữ đặc thù.

- **🕸️ Knowledge Graph & Learning Path:**
  - Tự động rút trích các **Concept (khái niệm)** và **Prerequisite (quan hệ tiên quyết)** từ tài liệu bằng LLM.
  - Sử dụng **NetworkX** để xây dựng đồ thị có hướng (DiGraph) và **Topological Sort** để đề xuất lộ trình học tuyến tính tối ưu.
  - Phát hiện chu trình (Cycle Detection) để cảnh báo logic sai lệch.

- **🧠 ReAct Agent & Tool Calling:**
  - Áp dụng kiến trúc **ReAct (Reasoning + Acting)** cho phép Agent tự suy luận và chọn công cụ phù hợp.
  - **Tools:** `search_docs` (tra cứu tài liệu), `generate_quiz` (tạo câu hỏi), `save_note` (lưu chú thích), `get_progress` (truy xuất tiến độ học tập).
  - Tích hợp **Memory 2 tầng** (Short-term context + Long-term ChromaDB user memory).

- **🎯 Quiz Arena & Cá nhân hóa:**
  - Tự động sinh bộ câu hỏi trắc nghiệm **theo từng Topic cụ thể** trong Concept Graph.
  - Theo dõi tiến trình (Progress Bar), chấm điểm ngay lập tức, lưu trữ % hoàn thành vào Database (SQLite + SQLAlchemy).

- **⚡ LLM Adapters:**
  - Tích hợp linh hoạt giữa **Gemini API** (Free Tier - tốc độ cao) và **Ollama local** (Qwen2.5 - hoàn toàn offline, private, fallback khi hết quota).

---

## 🛠️ Tech Stack (Định hướng Công nghệ)

- **UI & Workspace:** Streamlit (Functional UI 3 cột: Sidebar - Graph/Chat - Quiz)
- **Agent Orchestration:** Pure Python (No-Framework để tối ưu kiểm soát ReAct loop)
- **Validation Layer:** Pydantic V2 (Structured Outputs)
- **Embedding:** Gemini Embedding API (`text-embedding-004`) / `sentence-transformers` (`bge-m3`)
- **Vector Database:** ChromaDB + `rank-bm25`
- **Relational Database:** SQLite (ORM: SQLAlchemy)
- **Graph Processing:** NetworkX

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng

### 1. Yêu cầu hệ thống
- Python 3.10+
- Ollama (nếu muốn sử dụng local models như `qwen2.5:1.5b` làm fallback)

### 2. Cài đặt Dependencies

Clone repository và cài đặt các thư viện cần thiết:

```bash
git clone https://github.com/yourusername/ai-study-agent.git
cd ai-study-agent
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Tạo file `.env` từ `.env.example`:

```bash
cp .env.example .env
```

Mở file `.env` và điền API key của bạn:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Khởi chạy Ứng dụng

Chạy hệ thống với Streamlit:

```bash
streamlit run main.py
```
Giao diện Workspace sẽ tự động mở trên trình duyệt tại `http://localhost:8501`.

---

## 📁 Cấu trúc Dự án

```text
ai-study-agent/
├── src/
│   ├── agent/          # Orchestrator (ReAct loop), State, Prompt Templates, Tools
│   ├── db/             # SQLAlchemy Models & SQLite Engine
│   ├── documents/      # Logic xử lý Entity Document, File Parsing
│   ├── eval/           # Framework chấm điểm LLM-as-judge
│   ├── graph/          # Xây dựng Knowledge Graph (NetworkX), Topological Sort
│   ├── llm/            # LLM Adapters (Gemini, Ollama), JSON Parsers
│   ├── memory/         # Long-term Memory (ChromaDB), User Progress DB
│   └── rag/            # Semantic Chunker, Embedder, Hybrid Retriever, BM25
├── ui/
│   ├── components/     # UI Tái sử dụng (Sidebar, Chat, Quiz Arena, Graph Viewer, Auth)
│   └── router.py       # Điểu hướng trang giữa các chế độ học tập
├── main.py             # Entry point Streamlit
├── requirements.txt    # Danh sách thư viện Python
└── ai-study-agent.md   # Thiết kế & Kế hoạch triển khai (Single Source of Truth)
```

---

## 🧪 Đóng góp Học thuật (Academic Evaluation)

Một phần quan trọng của dự án là bộ **Evaluation Framework** (`src/eval/`) nhằm kiểm chứng giả thuyết:
> *"Agent+RAG (tích hợp công cụ và suy luận) có mang lại hiệu quả học tập cá nhân hóa tốt hơn RAG-only thuần túy hay không?"*

- Đánh giá sử dụng **LLM-as-judge** (offline local qua Ollama) theo 3 tiêu chí: `Faithfulness`, `Relevance`, và `Personalization`.
- Dataset đánh giá: Được xây dựng cẩn thận, bao gồm các câu hỏi factual (tra cứu), reasoning (suy luận nhiều bước) và personalized (cần bộ nhớ phiên trước).

---
*Developed by the AI Study Agent Team (Chương trình Sinh viên Công nghệ Tập sự).*
