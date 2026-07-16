# TÀI LIỆU THIẾT KẾ & KẾ HOẠCH TRIỂN KHAI DỰ ÁN: AI STUDY AGENT

**Vị trí định hướng:** AI Agent & Algorithm (Chương trình Sinh viên Công nghệ Tập sự)
**Kiến trúc:** Functional UI / Workspace-Centric (No-Framework Agent)

---

## 1. TỔNG QUAN DỰ ÁN (EXECUTIVE SUMMARY)

Dự án **AI Study Agent** là một hệ thống hỗ trợ học tập cá nhân hóa thế hệ mới. Khác biệt với các Chatbot RAG (Retrieval-Augmented Generation) truyền thống vốn thụ động và dựa vào văn bản tự do, hệ thống này được thiết kế theo mô hình **Functional UI (Giao diện chức năng)**.

Hệ thống đóng vai trò như một **Agent tự chủ (Autonomous Agent)**: tự phân tích tài liệu học tập, tự động kiến tạo bản đồ tri thức (Knowledge Graph), tự định hướng công cụ (Tool Calling) thông qua vòng lặp suy luận ReAct và chủ động thiết kế bài tập cá nhân hóa dựa trên điểm yếu của người học.

---

## 2. ĐỊNH HƯỚNG CÔNG NGHỆ (TECHNICAL STACK)

| Phân tầng               | Công nghệ lựa chọn                      | Lý do & Vai trò thuật toán                                                                                                     |
| :---------------------- | :-------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| **UI Layer**            | Streamlit                               | Xây dựng giao diện Workspace 3 cột nhanh chóng, quản lý trạng thái động (State-driven UI).                                     |
| **Orchestration**       | Python thuần (Pure Python) + Gemini SDK | Tự cài đặt vòng lặp ReAct, không phụ thuộc vào framework bên thứ ba để tối ưu hóa kiểm soát và chứng minh năng lực thuật toán. |
| **RAG & Search Engine** | ChromaDB + Rank-BM25                    | Công cụ tìm kiếm lai (Hybrid Search) kết hợp giữa tìm kiếm ngữ nghĩa (Dense) và từ khóa chính xác (Sparse).                    |
| **Graph Processing**    | NetworkX                                | Xử lý cấu trúc dữ liệu đồ thị, phát hiện chu trình và sắp xếp lộ trình học bằng Topological Sort.                              |
| **Database & Memory**   | SQLite + SQLAlchemy (ORM)               | Quản lý trạng thái tiến độ học tập có cấu trúc của người dùng.                                                                 |
| **Validation Layer**    | Pydantic V2                             | Định nghĩa chặt chẽ schema đầu ra (Structured Outputs) phục vụ hiển thị UI và giao tiếp giữa các module.                       |
| **Deployment**          | Docker + Hugging Face Spaces            | Đóng gói môi trường nhất quán, phân phối sản phẩm lên Cloud thực tế.                                                           |

---

## 3. CẤU TRÚC THƯ MỤC HỆ THỐNG (FOLDER STRUCTURE)

ai-study-agent/
├── .env # Lưu trữ API Keys (GEMINI_API_KEY) & Configs
├── README.md # Hướng dẫn chạy nhanh dự án
├── requirements.txt # Khai báo thư viện phụ thuộc
├── main.py # Điểm khởi chạy ứng dụng Streamlit (Entrypoint)
├── src/ # Thư mục mã nguồn cốt lõi
│ ├── **init**.py
│ ├── config.py # Cấu hình chung và các hằng số hệ thống
│ ├── agent/ # Bộ não quyết định (Orchestration)
│ │ ├── **init**.py
│ │ ├── orchestrator.py # Vòng lặp ReAct thuần Python (State Machine)
│ │ ├── prompt_templates.py # Hệ thống System Prompts điều phối
│ │ ├── state.py # Quản lý AgentState bằng Pydantic
│ │ └── tools/ # Đăng ký danh sách công cụ của Agent
│ │ ├── **init**.py
│ │ ├── base.py # Lớp cơ sở tự trích xuất JSON Schema cho Tool
│ │ ├── doc_retriever.py # Tool kết nối RAG
│ │ ├── graph_generator.py # Tool sinh cấu trúc Đồ thị kiến thức
│ │ ├── quiz_generator.py # Tool sinh Quiz trắc nghiệm có cấu trúc
│ │ └── progress_tracker.py # Tool đọc/ghi trạng thái SQLite
│ ├── rag/ # Tìm kiếm và Truy xuất Tri thức (RAG)
│ │ ├── **init**.py
│ │ ├── chunker.py # Thuật toán Semantic Chunking
│ │ ├── embedder.py # Quản lý Vector Embeddings
│ │ ├── indexing.py # Pipeline phân tích tài liệu PDF
│ │ └── hybrid_search.py # Thuật toán trộn kết quả Reciprocal Rank Fusion (RRF)
│ ├── graph/ # Xử lý đồ thị tri thức
│ │ ├── **init**.py
│ │ ├── graph_manager.py # Giải thuật đồ thị (Topological Sort, Cycle Check)
│ │ └── schemas.py # Pydantic Schemas của đồ thị (Nodes, Edges)
│ ├── memory/ # Quản lý bộ nhớ
│ │ ├── **init**.py
│ │ ├── local_db.py # SQLite: Lưu tiến độ học tập và lịch sử quiz
│ │ └── vector_store.py # ChromaDB: Bộ nhớ ngữ cảnh dài hạn dạng Vector
│ └── ui/ # Giao diện Workspace-Centric
│ ├── **init**.py
│ ├── dashboard.py # Module điều phối giao diện 3 cột chính
│ └── components/ # Các widgets tương tác động
│ ├── sidebar.py # Sidebar: Upload file & Hiển thị Thought Log
│ ├── graph_viewer.py # Cột giữa: Bản đồ lộ trình học tương tác
│ └── quiz_arena.py # Cột phải: Đấu trường luyện tập & Đánh giá
└── tests/ # Đánh giá thuật toán & Kiểm thử (Evaluation)
├── **init**.py
├── test_agent.py # Kiểm thử luồng ReAct Loop
└── eval_rag.py # Đánh giá RAG tự động (LLM-as-a-judge)
