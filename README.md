# Self Study Supporter

Ứng dụng hỗ trợ tự học từ PDF, hiện dùng Streamlit, PostgreSQL/SQLite và Chroma.
Nhánh `feature/docker-local-foundation` xây dựng nền tảng kỹ thuật Phase 0.

Đã triển khai: đăng ký/đăng nhập; PDF có text layer; semantic chunking với BGE-M3;
hybrid retrieval Dense + BM25 + RRF; custom ReAct với công cụ tìm tài liệu, quiz,
ghi chú và tiến độ; concept graph/lộ trình học; quiz lưu SQL; persistent Chroma.
Quiz chỉ được chấm khi có đúng bốn lựa chọn và một đáp án hợp lệ. PDF scan cần OCR.

Next.js, FastAPI, LangGraph, reranker và cá nhân hóa mastery thuộc roadmap, chưa
triển khai trong Phase 0. Chưa phát hành v1.0.0; chưa có benchmark chất lượng LLM.

## Chạy bằng Docker (PowerShell)

```powershell
git clone https://github.com/ManhT005/self-study_supporter.git
cd self-study_supporter
git switch feature/docker-local-foundation
Copy-Item .env.docker.example .env.docker
# Đổi POSTGRES_PASSWORD. Có thể để trống các key cloud.
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build --wait
```

Mở http://localhost:8501. Docker dùng Python 3.11/CPU và chạy migration trước app.
App khỏe không đồng nghĩa model đã sẵn sàng. BGE-M3 tải vào `hf_cache` khi ingest;
chat/quiz cần Ollama đã có model hoặc provider được cấu hình. Không tải model khi build.
Đọc [Docker/Ollama/backup](docs/operations/docker.md) trước khi thao tác dữ liệu.
POSIX dùng `cp` thay `Copy-Item`; các lệnh Compose giống nhau.

## Kiểm thử và phát triển

Python 3.11–3.12; dùng môi trường riêng. Bộ test nhanh không gọi model hoặc cloud.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
```

`backend/` là distribution `study-supporter` theo src-layout, không có runtime
framework dependency. Legacy `src/` và `ui/` được giữ lại; RRF forward sang package
mới và có golden tests. Không đổi thuật toán, model, vector dimension hoặc ID collection.
Các nhóm import được kiểm tra bằng AST; core không import UI, driver hoặc SDK.

- [Hướng dẫn đóng góp và command matrix](CONTRIBUTING.md)
- [Kiến trúc và ADR](docs/architecture/overview.md)
- [Kế hoạch Phase 0](docs/plans/PHASE_0_ENGINEERING_FOUNDATION.md)
- [Migration DB trống và adoption DB cũ](docs/operations/migrations.md)
- [Contract cho frontend tương lai](docs/api/README.md)
- [Kết quả nghiệm thu thực tế và phần còn thiếu](docs/reports/p0-acceptance.md)

Không commit `.env`, tài liệu người dùng, Chroma/SQL dumps hay model weights.
Dùng `down`/`up` để giữ volume; không dùng `down -v` với dữ liệu cần giữ.
DB cũ chưa có revision Alembic cần backup, schema comparison và review trước adoption.
