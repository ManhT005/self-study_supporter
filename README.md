# Self Study Supporter

Ứng dụng tự học từ PDF: đăng ký/đăng nhập, BGE-M3 semantic chunking, hybrid
Dense/BM25/RRF, ReAct chat kèm nguồn, quiz/progress và concept graph.
Code nghiệp vụ nằm trong `backend/src/study_supporter`; Streamlit ở
`apps/streamlit_legacy` gọi application services qua bootstrap.

Chạy Docker từ repository root (PowerShell):

```powershell
Copy-Item config/docker.env.example .env.docker
# Đặt POSTGRES_PASSWORD; cấu hình Ollama hoặc provider nếu cần chat/quiz.
docker compose --env-file .env.docker config --quiet
docker compose --env-file .env.docker up -d --build --wait
```

Mở http://localhost:8501. Docker chạy migration trước app và giữ SQL/Chroma/model
cache trong volume. BGE-M3 tải khi ingest lần đầu; chat/quiz cần model đã có ở
Ollama hoặc cloud provider. PDF scan cần OCR; quiz phải có bốn lựa chọn hợp lệ.

Phát triển/test offline, Python 3.11–3.12:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/dev.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
```

POSIX dùng `.venv/bin/`. Native UI cần runtime dependencies và migration; xem
[env mẫu](config/README.md) và [dependency locks](requirements/README.md).
`main.py` và `eval_test.py` là command redirects để giữ lệnh cũ hoạt động.

- [Kiến trúc](docs/architecture/overview.md) và [ADR consolidation](docs/architecture/adr/repository-consolidation.md)
- [Đóng góp và command matrix](CONTRIBUTING.md)
- [Docker/Ollama/backup](docs/operations/docker.md) và [migrations](docs/operations/migrations.md)
- [Kết quả refactor](docs/reports/repository-consolidation-acceptance.md)
- [Evaluation opt-in](evaluation/README.md)
- [HTTP API và frontend contract](docs/api/README.md)
- [Kế hoạch foundation lịch sử](docs/plans/PHASE_0_ENGINEERING_FOUNDATION.md) và [bằng chứng cũ](docs/reports/p0-acceptance.md)

Không commit env thật, PDF người dùng, dumps hoặc model weights. `down`/`up` giữ
volume; tránh `down -v` với dữ liệu cần giữ. Migration giao diện tái sử dụng core;
không thay schema/model/vector IDs.

## Next.js learning workspace preview

The document-first UI is in `apps/web`, with a FastAPI adapter in `apps/api`.
See [startup and validation](docs/operations/learning-workspace.md) and
[implementation decisions](docs/design/ui-v1/IMPLEMENTATION.md). Use
`compose.workspace.yaml` for an isolated preview; Streamlit remains available
until the migration's operational gates pass.
