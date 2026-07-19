# Sprint 1 Notes — RAG Pipeline

## Kết quả

Pipeline chạy end-to-end: `DSA.pdf` → parse (182 câu) → semantic chunking (30 chunk) → embed → ChromaDB → hybrid search. Test query "Dữ liệu là gì?" trả về đúng chunk liên quan ở vị trí #1.

## Kiến trúc & thuật toán tự viết

| Module                                  | Thuật toán                                                                                | Ghi chú                                                                                                        |
| --------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `pdf_parser.py`                         | PyMuPDF, giữ metadata (source, page_number)                                               | Không xử lý PDF scan (không có text layer)                                                                     |
| `chunker.py`                            | Semantic chunking: cosine distance giữa embedding câu liền kề, breakpoint = percentile 95 | Có heuristic chặn breakpoint tại câu kết thúc bằng `:` (tránh cắt đứt câu dẫn khỏi danh sách liệt kê phía sau) |
| `embedder.py` / `vector_store.py`       | Gemini/local embedding, ChromaDB 2 collection                                             | `chunk_id` = hash(source+page+text) → deterministic, dùng `upsert()` → idempotent                              |
| `bm25_index.py` + `hybrid_retriever.py` | BM25 (sparse) + dense (ChromaDB), trộn bằng Reciprocal Rank Fusion (k=60)                 | Query dùng `task_type=RETRIEVAL_QUERY`, chunk lưu dùng `RETRIEVAL_DOCUMENT`                                    |
| `embedding_provider.py`                 | Interface `EmbeddingProvider` (Dependency Inversion)                                      | 2 implementation: `GeminiEmbeddingProvider`, `LocalEmbeddingProvider` (bge-m3)                                 |

## Lỗi gặp phải & cách vá

| Vấn đề                                                        | Nguyên nhân                                                    | Giải pháp                                                                                                                                  |
| ------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `404 text-embedding-004 not found`                            | Model legacy, bị thay bằng `gemini-embedding-001`              | Đổi model + đổi SDK `google-generativeai` → `google-genai`                                                                                 |
| Chunk bị nhân đôi khi chạy lại script                         | `chunk_id` sinh bằng UUID ngẫu nhiên mỗi lần                   | Đổi sang `chunk_id` deterministic (hash nội dung) + `upsert()` thay vì `add()`                                                             |
| Breakpoint sai tại câu liệt kê ("...hai tiêu chuẩn sau đây:") | Câu kết bằng `:` có embedding khác biệt bất thường với câu sau | Loại breakpoint nếu câu kết thúc bằng `:`                                                                                                  |
| `429 RESOURCE_EXHAUSTED` (per-minute, limit 100)              | Gọi API embedding từng câu một, không batch                    | Batch nhiều text/request + `RateLimiter` (leaky bucket, ép khoảng cách tối thiểu giữa request) + đọc `retryDelay` từ response thay vì đoán |
| `429 RESOURCE_EXHAUSTED` (per-day, limit 1000)                | Debug lặp lại nhiều lần trong ngày, cộng dồn quota             | Không thể retry — chuyển hẳn sang `LocalEmbeddingProvider` (bge-m3) cho giai đoạn phát triển, giữ Gemini cho demo/eval                     |

EROR: Google thường xuyên deprecate model nhanh hơn thông báo chính thức — nên kiểm tra tên model hiện tại trước khi demo/bảo vệ, không tin tưởng tuyệt đối vào tên model đã hardcode từ trước

## Quyết định kiến trúc quan trọng

**Multi-provider embedding** qua interface `EmbeddingProvider`: code nghiệp vụ (`chunker`, `embedder`) không phụ thuộc trực tiếp Gemini SDK, chỉ phụ thuộc abstraction → đổi Gemini ↔ Local ↔ (sau này) Ollama chỉ cần đổi 1 dòng khởi tạo, không sửa logic pipeline. Lý do: free tier Gemini không đủ cho nhịp độ debug thực tế của 1 người/team nhỏ.

## Việc còn để ngỏ (không chặn Sprint 2)

- Chưa xử lý PDF dạng scan (không có text layer)
- `LocalEmbeddingProvider` (768 chiều Gemini vs 1024 chiều bge-m3) — nhớ xóa `data/chroma_db/` khi đổi provider, dimension không tương thích ngược
- Chưa benchmark định lượng dense-only vs hybrid (mới quan sát định tính qua 1-2 câu hỏi)
