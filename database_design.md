# Thiết kế Database — AI Study Agent

## 1. Nguyên tắc thiết kế

Hệ thống có **2 tầng lưu trữ khác bản chất**, không gộp chung:

- **Postgres (quan hệ)** — dữ liệu có cấu trúc, cần truy vấn chính xác, thống kê, ràng buộc toàn vẹn: tài khoản, tiến độ học tập, metadata tài liệu.
- **ChromaDB (vector)** — dữ liệu cần tìm kiếm theo *ngữ nghĩa* (semantic search): nội dung tài liệu đã embed, ghi chú dài hạn.

Nguyên tắc liên kết: **Postgres giữ metadata + ID, ChromaDB giữ vector** — 2 bên nối với nhau qua `user_id`/`document_id` dùng chung, không trùng lặp logic ở cả 2 nơi.

Mức độ chuẩn hóa: dừng ở 3NF cho phần cần truy vấn chính xác (users, documents, quiz_attempts), **không chuẩn hóa quá tay** phần nội dung do LLM sinh động (quiz, concept graph) — lưu dạng JSON/text thay vì tách bảng con, vì các phần này đọc theo khối, không cần query từng field riêng lẻ (tránh over-engineering không cần thiết).

---

## 2. Sơ đồ quan hệ tổng quan (ERD dạng text)

```
┌─────────────┐        ┌──────────────────┐        ┌─────────────────┐
│   users     │1      N│    documents      │1      N│  quiz_attempts   │
│─────────────│───────▶│──────────────────│───────▶│──────────────────│
│ id (PK)     │        │ id (PK)          │        │ id (PK)          │
│ username    │        │ user_id (FK)     │        │ user_id (FK)     │
│ password_   │        │ filename         │        │ document_id (FK) │
│   hash      │        │ status           │        │ topic            │
│ created_at  │        │ page_count       │        │ question         │
└─────────────┘        │ chunk_count      │        │ is_correct       │
      │1                │ chroma_          │        │ created_at       │
      │                 │   collection     │        └──────────────────┘
      │N                │ concept_graph_   │
┌─────────────┐         │   json           │
│   notes      │        │ created_at       │
│─────────────│         └──────────────────┘
│ id (PK)     │                  │1
│ user_id(FK) │                  │
│ content     │                  │N  (tùy chọn, đề xuất mở rộng)
│ created_at  │         ┌──────────────────┐
└─────────────┘         │  chat_messages    │
                         │──────────────────│
                         │ id (PK)          │
                         │ user_id (FK)     │
                         │ document_id (FK) │
                         │ role             │
                         │ content          │
                         │ created_at       │
                         └──────────────────┘

Ngoài Postgres — tầng vector (ChromaDB), liên kết qua user_id/document_id:

┌────────────────────────────┐        ┌────────────────────────────┐
│ documents_<user_id>        │        │ user_memory                │
│ (1 collection / user)      │        │ (1 collection chung, lọc   │
│─────────────────────────── │        │  bằng metadata user_id)    │
│ id = chunk_id (content hash)│        │ id = note_id (khớp notes.id)│
│ embedding                  │        │ embedding                  │
│ document = chunk text      │        │ document = note content    │
│ metadata: source,          │        │ metadata: user_id           │
│   page_start, page_end     │        │                             │
└────────────────────────────┘        └────────────────────────────┘
```

---

## 3. Chi tiết từng bảng (Postgres)

### 3.1 `users` — **Đã implement**

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `username` | String | UNIQUE, NOT NULL, indexed | |
| `password_hash` | String | NOT NULL | bcrypt, không lưu plaintext |
| `created_at` | DateTime | default now() | |

### 3.2 `documents` — **Đề xuất thêm** (hiện chưa có bảng này, metadata tài liệu đang "vô hình" — chỉ tồn tại dưới dạng tên collection ChromaDB, không tra cứu/thống kê được từ Postgres)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `user_id` | Integer | FK → `users.id`, NOT NULL, indexed | 1 user có N documents |
| `filename` | String | NOT NULL | tên file gốc, hiển thị lại cho user |
| `chroma_collection_name` | String | NOT NULL | `documents_<user_id>` — tên collection tương ứng trong ChromaDB |
| `status` | String | NOT NULL, default `'processing'` | `processing` \| `ready` \| `failed` — để UI biết hiển thị trạng thái đúng, không chỉ dựa vào session_state (bền hơn qua các lần deploy) |
| `page_count` | Integer | nullable | |
| `chunk_count` | Integer | nullable | |
| `concept_graph_json` | JSONB | nullable | Lưu nguyên `{"nodes": [...], "edges": [...]}` — **không tách bảng `nodes`/`edges` riêng**: graph nhỏ (~10 node), luôn đọc/viết theo khối, tách bảng chỉ thêm JOIN không cần thiết |
| `created_at` | DateTime | default now() | |

**Vì sao cần bảng này:** đây là mảnh còn thiếu quan trọng nhất hiện tại — `concept_graph` và trạng thái xử lý tài liệu chỉ sống trong `st.session_state`, mất hoàn toàn khi đăng xuất/container restart. Thêm bảng này giải quyết đúng gốc rễ vấn đề "phải upload lại" một cách bền vững hơn cách "tự động resume từ ChromaDB" đã làm tạm trước đó.

### 3.3 `quiz_attempts` — **Đã implement**, đề xuất thêm 1 cột

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `user_id` | String/Integer | FK → `users.id`, NOT NULL, indexed | |
| `document_id` | Integer | FK → `documents.id`, **nullable** *(đề xuất thêm)* | Biết câu hỏi thuộc tài liệu nào — cần khi 1 user có nhiều tài liệu |
| `topic` | String | NOT NULL | |
| `question` | String | NOT NULL | |
| `is_correct` | Integer (0/1) | NOT NULL | |
| `created_at` | DateTime | default now() | |

**Không tách `quizzes`/`quiz_questions` riêng:** quiz do LLM sinh động mỗi lần, không phải danh mục cố định cần tra cứu lại từng câu — lưu denormalized (topic + question dạng text ngay trong `quiz_attempts`) là đủ và tránh phức tạp hóa không cần thiết.

### 3.4 `notes` — **Đề xuất thêm** (mirror của ChromaDB `user_memory`)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `id` | String (UUID) | PK | Dùng chung làm `id` bên ChromaDB (`user_memory` collection) — 1 ID, 2 nơi lưu 2 phần khác nhau của cùng 1 note |
| `user_id` | Integer | FK → `users.id`, NOT NULL, indexed | |
| `content` | Text | NOT NULL | Bản sao nội dung note — cho phép liệt kê/tra cứu nhanh từ Postgres, không phải lúc nào cũng cần semantic search |
| `created_at` | DateTime | default now() | |

**Lý do lưu song song ở cả 2 nơi:** Postgres cho truy vấn chính xác ("liệt kê tất cả ghi chú của tôi theo thời gian"), ChromaDB cho truy vấn ngữ nghĩa ("tìm ghi chú liên quan tới X"). Đây là pattern phổ biến khi kết hợp relational + vector store, không phải trùng lặp dữ liệu vô nghĩa.

### 3.5 `chat_messages` — **Đề xuất mở rộng** (chưa cấp thiết, ghi vào hướng phát triển)

| Cột | Kiểu | Ràng buộc | Ghi chú |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `user_id` | Integer | FK → `users.id`, NOT NULL, indexed | |
| `document_id` | Integer | FK → `documents.id`, nullable | |
| `role` | String | NOT NULL | `user` \| `assistant` |
| `content` | Text | NOT NULL | |
| `created_at` | DateTime | default now() | |

**Hiện tại:** `chat_history` chỉ sống trong `st.session_state`, mất khi đăng xuất/refresh. Thêm bảng này để lịch sử chat bền vững qua các lần đăng nhập — **chưa làm ở giai đoạn này**, độ ưu tiên thấp hơn `documents` (vì mất chat history ít nghiêm trọng hơn mất metadata tài liệu/graph).

---

## 4. Tầng Vector Store (ChromaDB) — không thuộc schema quan hệ, nhưng là 1 phần thiết kế dữ liệu tổng thể

| Collection | Vai trò | Cách ly | Liên kết với Postgres |
|---|---|---|---|
| `documents_<user_id>` | Chunk + embedding của tài liệu | **1 collection riêng/user** (không dùng chung + filter metadata, vì `chunk_id` tính từ content hash sẽ trùng giữa 2 user upload cùng file) | Tên collection lưu ở `documents.chroma_collection_name` |
| `user_memory` | Ghi chú dài hạn (embedding) | Dùng chung 1 collection, lọc bằng metadata `user_id` (đã đúng từ Sprint 4, vì `note_id` là UUID ngẫu nhiên — không lo trùng giữa user) | `id` khớp với `notes.id` |

---

## 5. Bảng tổng hợp quan hệ

| Quan hệ | Loại | Ý nghĩa |
|---|---|---|
| `users` → `documents` | 1 – N | 1 user có thể có nhiều tài liệu |
| `users` → `quiz_attempts` | 1 – N | 1 user có nhiều lượt làm quiz |
| `documents` → `quiz_attempts` | 1 – N | 1 tài liệu là nguồn cho nhiều lượt quiz |
| `users` → `notes` | 1 – N | 1 user có nhiều ghi chú |
| `users` → `chat_messages` | 1 – N | (đề xuất) 1 user có nhiều lượt chat |
| `documents` → `chat_messages` | 1 – N | (đề xuất) 1 tài liệu là ngữ cảnh cho nhiều lượt chat |

Không có quan hệ N–N nào trong hệ thống hiện tại — mọi thứ đều sở hữu bởi đúng 1 `user`, không có khái niệm chia sẻ/nhiều-người-cùng-sở-hữu 1 tài liệu.

---

## 6. Index & ràng buộc nên có

```sql
-- Unique + index đã có qua SQLAlchemy khai báo, liệt kê lại để rõ ràng khi review:
CREATE UNIQUE INDEX ix_users_username ON users(username);
CREATE INDEX ix_documents_user_id ON documents(user_id);
CREATE INDEX ix_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX ix_notes_user_id ON notes(user_id);

-- Ràng buộc xóa theo chuỗi (khi xóa user, dọn sạch dữ liệu liên quan, không để rác):
ALTER TABLE documents ADD CONSTRAINT fk_documents_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE quiz_attempts ADD CONSTRAINT fk_quiz_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

**Lưu ý:** `ON DELETE CASCADE` ở Postgres chỉ dọn được dữ liệu Postgres — nếu xóa user, vẫn cần code dọn thêm ChromaDB collection tương ứng (`documents_<user_id>`) thủ công, vì ChromaDB không nằm trong transaction của Postgres.

---

## 7. Khuyến nghị quản lý migration (Alembic)

Hiện tại schema được tạo bằng `Base.metadata.create_all(engine)` — chỉ phù hợp lúc **tạo bảng lần đầu**, không xử lý được việc **sửa đổi schema sau này** (ví dụ thêm cột `document_id` vào `quiz_attempts` như đề xuất ở mục 3.3). Với dự án ở quy mô báo cáo/bảo vệ, dùng `create_all` là đủ — nhưng nếu muốn thể hiện thực hành chuyên nghiệp hơn trong báo cáo, có thể setup **Alembic** để quản lý version schema:

```bash
pip install alembic
alembic init migrations
# Sau đó mỗi lần đổi model -> alembic revision --autogenerate -m "..."
#                           -> alembic upgrade head
```

Không bắt buộc phải làm ngay — ghi vào "hướng phát triển" nếu không còn thời gian, thể hiện bạn hiểu đây là thực hành đúng của một hệ thống có schema thay đổi theo thời gian.
