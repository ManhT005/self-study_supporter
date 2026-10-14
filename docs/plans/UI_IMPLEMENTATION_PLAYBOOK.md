# UI Implementation Playbook — Self Study Supporter

- **Mục đích:** hướng dẫn người phát triển tự triển khai giao diện mới dựa trên sketch đã tạo, theo từng bước có thể kiểm chứng.
- **Repository:** `ManhT005/self-study_supporter`
- **Nhánh làm việc:** `feature/ui-learning-workspace`
- **Base:** nhánh kế hoạch `docs/nextjs-fastapi-migration-plan`, xuất phát từ `develop`; không làm trên `main`.
- **Trạng thái:** execution plan — chưa phải bằng chứng rằng Next.js/FastAPI đã được triển khai.
- **Tài liệu kiến trúc tổng thể:** [FRONTEND_MIGRATION_NEXTJS_FASTAPI.md](./FRONTEND_MIGRATION_NEXTJS_FASTAPI.md)

---

## 1. Mục tiêu và cách sử dụng tài liệu

Hãy làm theo thứ tự các phase bên dưới. Mỗi phase phải có kết quả chạy được, test và commit riêng. Không cố hoàn thành toàn bộ giao diện bằng dữ liệu giả rồi mới bắt đầu nghĩ đến API.

Kết quả cuối cần có:

1. Next.js + TypeScript là frontend chính, responsive theo desktop/mobile sketch.
2. FastAPI là HTTP boundary, xác thực người dùng và kiểm tra ownership trước khi gọi use case.
3. Các use case, AI/RAG, embedding, retrieval, SQLAlchemy và Chroma hiện có tiếp tục được tái sử dụng.
4. UI có trạng thái loading, empty, success, error và retry rõ ràng; citations phản ánh evidence thật.
5. Docker/CI có thể build và kiểm tra web/API mà không cần Streamlit.
6. Chỉ xóa Streamlit sau khi feature parity, regression, backup/restore và rollback đã đạt gate.

**Nguyên tắc:** triển khai một vertical slice hoàn chỉnh mỗi lần: UI → API contract → FastAPI → application use case → persistence/provider → kết quả UI. Không đổi thuật toán RAG chỉ để phù hợp với frontend.

## 2. Sketch và quy tắc thiết kế phải tuân thủ

### Bộ sketch đã tạo

Các file dưới đây được tạo ở cuộc trao đổi thiết kế trước. Chúng chưa nằm trong cây file của nhánh `develop` tại thời điểm lập kế hoạch; trước khi triển khai UI, hãy lưu/copy chúng vào repository để team và CI review được cùng một nguồn tham chiếu.

Đề xuất lưu thành:

- `docs/design/ui-v1/assets/SELF_STUDY_SUPPORTER_UI_DESIGN_BOARD.png`
- `docs/design/ui-v1/assets/SELF_STUDY_SUPPORTER_MOBILE_WIREFRAMES.png`
- `docs/design/ui-v1/MASTER_PLAN.md` — bản design master plan nếu muốn version-control toàn bộ đặc tả thiết kế.

Nguồn tham chiếu ban đầu: `SELF_STUDY_SUPPORTER_UI_DESIGN_BOARD.png`, `SELF_STUDY_SUPPORTER_MOBILE_WIREFRAMES.png` và `SELF_STUDY_SUPPORTER_UI_UX_V1_MASTER_PLAN.md` trong các file đã tạo ở cuộc trò chuyện trước. Không thay các sketch này bằng ảnh minh họa mới nếu chưa có quyết định thiết kế mới.

### Cách đọc sketch

- **Desktop design board:** chuẩn tham chiếu về sidebar, dashboard, AI Tutor, kế hoạch học, quiz, thư viện tài liệu và tiến độ.
- **Mobile wireframes:** chuẩn tham chiếu cho Hôm nay, AI Tutor và Luyện tập; một cột, thao tác chính rõ ràng, bottom navigation, citation mở bằng bottom sheet.
- **Design master plan:** nguồn chi tiết về IA, state matrix, accessibility, tokens, flows và acceptance. Nếu hình có chữ nhỏ/méo do sinh ảnh, ưu tiên đặc tả chữ trong master plan này.

### Không được tự ý làm lệch

- Desktop có global sidebar; mobile có bottom navigation 4 mục: **Hôm nay / Môn học / Luyện tập / Tiến độ**.
- Một màn hình có một CTA chính; tránh nhồi nhiều thẻ chỉ để giống dashboard quản trị.
- AI Tutor desktop dùng hai pane có thể thu gọn: đọc tài liệu và trợ giảng. Mobile chuyển sang một pane với tab **Đọc / Hỏi AI**; citations mở bottom sheet.
- Quiz hiển thị **một câu mỗi màn**, 4 lựa chọn dễ bấm, tiến độ câu hỏi và giải thích sau khi nộp.
- Nguồn trích dẫn phải đến từ response backend. Không tự sinh nhãn nguồn, số trang hoặc evidence giả.
- Không hiển thị raw chain-of-thought/Thought Log. Chỉ hiển thị trạng thái an toàn như “Đang tìm bằng chứng”, “Đang kiểm tra nguồn”.
- Mục tiêu accessibility: keyboard/focus đầy đủ, nhãn cho controls, thông báo lỗi dễ hiểu, reduced motion và vùng chạm mobile ưu tiên tối thiểu 44×44 CSS px.

### Design tokens khởi đầu

Dùng token tập trung, không hard-code màu/radius/spacing khác nhau trong từng trang. Token cụ thể có thể được điều chỉnh sau khi so với sketch:

- Primary: blue gần `#2563eb`; ink: navy gần `#0f172a`; background: `#f8fafc`; border: `#e2e8f0`.
- Card radius khoảng 16px; control radius khoảng 10px.
- Khoảng cách dựa trên bội số 4px.
- Light theme trước; chỉ thêm dark theme sau khi component/tokens hoạt động thống nhất.
- Màu không được là cách duy nhất để biểu thị trạng thái đúng/sai hoặc processing.

## 3. Kiểm tra baseline trước khi viết code

Repository hiện tại đã có core/application layer, Streamlit adapter, PostgreSQL/SQLAlchemy, Chroma và CI. Nhưng FastAPI runtime và Next.js app chưa tồn tại như sản phẩm chạy được; `docs/api/openapi.yaml` hiện chỉ là **proposal cho retrieval**, không phải API đã triển khai.

Các đường dẫn cần đọc trước khi sửa:

- Core composition/lifecycle: `backend/src/study_supporter/bootstrap.py`
- Auth use case: `backend/src/study_supporter/application/use_cases/authenticate.py`
- Document ownership: `backend/src/study_supporter/application/use_cases/documents.py`
- Ingestion: `backend/src/study_supporter/application/use_cases/ingest_document.py`
- Answer/chat: `backend/src/study_supporter/application/use_cases/answer_question.py`
- Quiz/progress: `backend/src/study_supporter/application/use_cases/generate_quiz.py`, `backend/src/study_supporter/application/use_cases/learning.py`
- Streamlit bridge và màn hình hiện có: `apps/streamlit_legacy/application_bridge.py`, `apps/streamlit_legacy/main.py`, `apps/streamlit_legacy/router.py`, `apps/streamlit_legacy/components/`
- API proposal: `docs/api/README.md`, `docs/api/openapi.yaml`
- Compose/Docker: `compose.yaml`, `Dockerfile`
- Migration: `backend/alembic.ini`, `backend/migrations/`
- CI: `.github/workflows/quality.yml`

### Baseline commands — Windows PowerShell

Chạy từ thư mục gốc repository. Giữ lại output/test failure để so sánh sau từng phase.

```powershell
git status --short
git branch --show-current
git log --oneline -5

python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/dev.txt
.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e ./backend
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py
```

Nếu môi trường đã có `.venv`, không cần tạo lại. Nếu một lệnh baseline đỏ, xác định đó là lỗi tồn tại từ trước hay lỗi do thay đổi mới; không xóa/skip test để làm xanh giả.

### Thao tác lấy nhánh

Nếu clone chưa có nhánh local:

```powershell
git fetch origin
git switch --track origin/feature/ui-learning-workspace
git status --short
```

Nếu đã có nhánh local:

```powershell
git switch feature/ui-learning-workspace
git pull --ff-only
```

Không chạy `git reset --hard`, `docker compose down -v` hoặc xóa volume dữ liệu trong migration này.

## 4. Thực tế hiện trạng phải giữ đúng

### Core có thể tái sử dụng

- `ApplicationFactory` quản lý resource process-scoped.
- Application layer đã có use case cho authentication, documents, ingestion, answer/retrieval, quiz submission và progress.
- Document hiện có ownership theo user và trạng thái processing/ready/failed.
- Ingestion hiện là use case synchronous có callback progress; chưa được mặc định coi là durable background job.
- Quiz history trong Streamlit đang dùng session state; không cam kết history được persist qua restart nếu chưa có backend storage/test chứng minh.
- Streamlit gọi application layer qua adapter; không copy logic Python sang TypeScript.

### Các bẫy cần tránh

1. **Course chưa được xác nhận là domain resource persisted.** Schema hiện tại có User, Document và QuizAttempt; không tự giả định đã có bảng Course. Trước khi làm CRUD môn học thật, chốt một lựa chọn:
   - **MVP khuyến nghị:** vertical slice đầu dùng document workspace, dùng navigation “Môn học” như hướng IA nhưng không tạo dữ liệu course giả; hoặc
   - tạo Course aggregate/schema bằng ADR + Alembic migration + test ownership riêng. Đây là thay đổi domain/data, không được lén nhét vào PR giao diện.
2. **Không có FastAPI session chỉ vì có Authentication use case.** Core auth trả `AppContext`; API phải bổ sung HTTP session/auth adapter.
3. **Không có job queue bền vững chỉ vì có progress callback.** Chốt ingestion dispatch, status polling và restart recovery trước khi UI hứa progress.
4. **Không chạy Streamlit và API cùng ghi vào một Chroma persistence path** nếu chưa xác minh multi-process safety. Dùng bản sao dữ liệu hoặc một writer duy nhất trong dual-run.
5. **Không đổi model embedding/vector dimension, collection naming, chunk IDs hoặc database volume** trong quá trình chuyển UI.
6. **Không expose user_id trong request như nguồn xác thực.** Identity phải đến từ session đã xác thực; mọi document/progress/notes route phải scope theo principal.
7. **Không để frontend gọi Ollama/provider trực tiếp** hoặc chứa provider API key.

## 5. Kiến trúc và cấu trúc thư mục mục tiêu

Giữ core framework-independent. Đề xuất cấu trúc thêm mới:

```text
apps/
  api/
    app/
      main.py
      lifespan.py
      dependencies.py
      routers/
        auth.py
        documents.py
        chat.py
        quiz.py
        progress.py
      schemas/
        auth.py
        documents.py
        chat.py
        quiz.py
        common.py
    tests/
  web/
    src/
      app/
        (public)/
          login/page.tsx
          register/page.tsx
        (workspace)/
          dashboard/page.tsx
          documents/page.tsx
          documents/[documentId]/page.tsx
          documents/[documentId]/study/page.tsx
          practice/page.tsx
          progress/page.tsx
          settings/page.tsx
        layout.tsx
        globals.css
      components/
        layout/
        ui/
        learning/
      features/
        auth/
        dashboard/
        documents/
        tutor/
        quiz/
        progress/
      lib/
        api/
        schemas/
        mocks/
        formatters/
      tests/
      e2e/
docs/
  design/
    ui-v1/
      assets/
      MASTER_PLAN.md
```

Đây là target layout, không phải yêu cầu phải tạo mọi file ngay ở commit đầu. Nếu repository đang có quy ước khác hợp lý, giữ nhất quán và cập nhật tài liệu thay vì tạo hai cấu trúc song song.

### Ranh giới module

- `apps/web`: presentation, routing, form state, loading/error/empty state.
- `apps/api`: HTTP, auth/session, DTO validation, status/error mapping, request ID.
- `backend/src/study_supporter`: domain, use cases, AI/RAG, ports/adapters nghiệp vụ hiện tại.
- Không import FastAPI/Next.js vào core.
- API route gọi use case/facade có sẵn qua composition root; không gọi ORM/Chroma trực tiếp trong route.
- Không cache `LearningSession` theo biến global. Resource process-scoped có thể shared; session/tool/conversation phải scoped theo principal và document.

## 6. Stack và quy ước frontend

Chọn một stack duy nhất, không tạo nhiều app thử nghiệm song song:

- Next.js App Router + TypeScript strict.
- Tailwind CSS + shadcn/ui (hoặc component library khác nếu đã được chốt; không trộn nhiều thư viện tương đương).
- Zod cho parse/validate dữ liệu đầu vào ở frontend.
- TanStack Query cho server state khi bắt đầu tích hợp API; không dùng Zustand/Redux chỉ để chứa dữ liệu có thể lấy lại từ server.
- Vitest + Testing Library cho component/logic tests; Playwright cho E2E khi vertical slice đã ổn định.
- Node LTS được Next.js hỗ trợ; pin version trong `.nvmrc`/tooling và CI. Giữ một package manager và một lockfile.
- Không để API secret trong `NEXT_PUBLIC_*`; mọi biến public đều được coi là có thể đọc từ browser.

Tạo app từ repository root:

```powershell
npx create-next-app@latest apps/web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
Set-Location apps/web
npm run dev
```

Nếu CLI thay đổi option ở phiên bản bạn cài, dùng option tương đương nhưng giữ App Router, TypeScript, Tailwind và ESLint. Ghi lại Node/Next versions trong PR.

Các scripts frontend tối thiểu cần có sau khi scaffold:

- `dev`
- `lint`
- `typecheck`
- `test`
- `build`

Không thêm script giả chạy thành công mà không thực thi test thực.

## 7. Phase 0 — Chốt scope, sketch assets và contract

**Commit gợi ý:** `docs(ui): freeze UI routes and sketch references`

### Việc cần làm

- [ ] Tạo thư mục `docs/design/ui-v1/assets/` và đưa hai ảnh sketch vào đó.
- [ ] Đưa design master plan vào repository nếu muốn review cùng code.
- [ ] Viết inventory ngắn: hành vi Streamlit nào phải giữ, use case nào hỗ trợ, test nào chứng minh.
- [ ] Quyết định Course domain: document-first MVP hay schema Course riêng.
- [ ] Chốt auth transport/session, CSRF/Origin, cookie flags và expiry.
- [ ] Chốt ingestion response/status/retry/restart semantics.
- [ ] Chốt chat response: synchronous hay SSE; nếu SSE, định nghĩa event schema và reconnect/cancel.
- [ ] Mở rộng `docs/api/openapi.yaml` trước hoặc cùng implementation; đánh dấu rõ proposal vs endpoint đã chạy.
- [ ] Ghi rõ feature nào sẽ defer; không thêm tính năng ngoài feature parity mà chưa duyệt.

### Output phải có

- Route map và navigation desktop/mobile.
- API-to-use-case mapping cho từng route.
- Danh sách DTO/error/status code.
- Quyết định được ghi lại cho Course, auth và ingestion.
- Acceptance checklist cho vertical slice đầu tiên: login → upload PDF → ready → hỏi AI → citation thật.

### Gate

Không bắt đầu API/UI feature integration nếu còn mơ hồ về ownership/auth hoặc ingestion status. Có thể dựng static shell bằng fixture trong lúc contract được review, nhưng fixture không được coi là backend capability.

## 8. Phase 1 — Frontend foundation và design system

**Commit gợi ý:** `feat(web): scaffold responsive learning workspace`

### Công việc theo thứ tự

1. Scaffold `apps/web`; xác nhận `npm run dev`, lint, typecheck và production build.
2. Thiết lập font, CSS reset, design tokens và light theme.
3. Tạo primitive components: Button, Input, Textarea, Select, Tabs, Dialog, Sheet, Badge, Progress, Skeleton, Toast, EmptyState, ErrorState, Breadcrumb.
4. Tạo `NavigationShell`: desktop sidebar, mobile bottom nav, main content width và responsive breakpoint.
5. Tạo authenticated shell placeholder, avatar/settings entry, page title/breadcrumb và sign-out action placeholder.
6. Tạo reusable states: loading, empty, error, permission denied, offline/reconnect.
7. Thêm component tests cho navigation active state, mobile nav, button disabled/pending và error display.
8. So sánh screenshot local với sketch tại 1440px, 1024px, 768px và 390px; sửa layout trước khi thêm nhiều trang.

### Điều kiện nghiệm thu

- [ ] Không có horizontal overflow trên phone.
- [ ] Sidebar không chiếm phần lớn màn hình ở laptop hẹp.
- [ ] Mobile chỉ có 4 bottom-nav items; Settings nằm trong avatar/menu.
- [ ] Keyboard có thể đi qua nav và form; focus ring nhìn thấy.
- [ ] Component không có style global gây ảnh hưởng chéo.
- [ ] Build/lint/typecheck chạy độc lập khỏi backend và Streamlit.

### Không làm ở phase này

Không làm chatbot thật, upload thật, database mới hay API auth giả. Dùng fixture có type rõ để xây layout; các nút chưa có hành vi phải được ẩn/disabled và ghi TODO, không giả vờ hoàn thành.

## 9. Phase 2 — FastAPI runtime và authentication

**Commit gợi ý:** `feat(api): add FastAPI runtime and session auth`

### Backend tasks

- [ ] Tạo adapter tại `apps/api`, không đặt import FastAPI trong core package.
- [ ] Thêm FastAPI/Uvicorn thành dependency trực tiếp, pin version và cập nhật lock/dependency docs theo quy ước repo.
- [ ] Tạo app factory và lifespan để tạo `ApplicationFactory` một lần/process và close resources khi shutdown.
- [ ] Thêm `GET /health/live` và `GET /health/ready`; readiness không được tải embedding model hay gọi cloud provider.
- [ ] Thêm request ID, structured logging và exception mapping.
- [ ] Tạo DTO HTTP riêng; không trả ORM model hoặc `AppContext` thô.
- [ ] Nối register/login vào Authentication use case hiện có.
- [ ] Triển khai session adapter theo ADR: opaque random token, cookie HttpOnly, Secure ở HTTPS, SameSite đã chốt, expiry và revoke khi logout.
- [ ] Bảo vệ write endpoints bằng CSRF/Origin policy phù hợp với same-origin frontend.
- [ ] Giới hạn brute force/rate limit cho login/register.
- [ ] Tạo dependency lấy principal từ session; không nhận user_id do browser tự gửi.
- [ ] Test session hết hạn, logout, cookie flags, invalid credentials và giả mạo user.

### API contract tối thiểu

Contract path có thể thay đổi theo ADR nhưng phải nhất quán. Đề xuất:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Response không bao giờ chứa password hash, raw session token hoặc provider secret. Nếu API chạy same-origin qua Next.js proxy, không mở CORS wildcard.

### Điều kiện nghiệm thu

- [ ] API startup/shutdown sạch.
- [ ] Auth không phụ thuộc Streamlit session state.
- [ ] Sau logout/expiry, protected endpoint trả 401.
- [ ] API test chứng minh client không thể giả mạo principal.
- [ ] Existing Python unit/contract/PostgreSQL tests vẫn xanh.
- [ ] Không thay schema ngoài migration đã được duyệt.

## 10. Phase 3 — UI auth và authenticated shell

**Commit gợi ý:** `feat(web): integrate login and protected workspace`

### Công việc

- [ ] Làm trang `/login` và `/register` theo design tokens; có pending/error/success state.
- [ ] Tạo một API client tập trung trong `src/lib/api/`; không hard-code fetch URL trong từng component.
- [ ] Ưu tiên same-origin `/api`; nếu cần proxy, chỉ cấu hình server-side URL.
- [ ] Tạo `AuthProvider`/server session check phù hợp với kiến trúc đã chọn; tránh duplicate request khi chuyển trang.
- [ ] Bảo vệ route ở UX layer nhưng vẫn dựa vào API authorization thật.
- [ ] Khi session hết hạn, thông báo rõ và đưa người dùng về login; không loop redirect.
- [ ] Logout phải clear UI state, query cache và selected document/session để tránh lộ data khi đổi tài khoản.
- [ ] Viết test: login success/failure, duplicate submit, refresh trang, logout, 401/expired session.

### Điều kiện nghiệm thu

Người dùng có thể đăng nhập, reload, mở workspace và logout. Không lưu bearer/session token trong localStorage. Không bundle server secrets vào frontend. Route guard ở frontend không được coi là security boundary.

## 11. Phase 4 — Document library và upload/ingestion

**Commit gợi ý:** `feat(web): add document library and ingestion status`

### API/use-case tasks

- [ ] Map list/get document sang `OwnedDocuments` hoặc facade tương đương.
- [ ] Tạo endpoint upload multipart PDF và validate file ở backend.
- [ ] Giữ MIME/content validation, size limit, duplicate SHA-256 behavior và cleanup file tạm hiện có.
- [ ] Chốt API trả đồng bộ hay 202 + job/document ID. Nếu 202, endpoint status phải trả trạng thái thực.
- [ ] Vì use case ingestion hiện chạy synchronous và chỉ có callback progress, quyết định bounded worker/queue và restart behavior trong ADR; không gọi `BackgroundTasks` là durable queue.
- [ ] Chạy công việc embedding/parser nặng ngoài event loop async.
- [ ] Giới hạn số job đồng thời và tài nguyên.
- [ ] Nếu chưa có durable queue, ghi rõ giới hạn khi API restart; UI không được hứa resume nếu backend chưa hỗ trợ.
- [ ] Dùng status polling với interval có giới hạn/backoff; dừng polling khi READY/FAILED hoặc rời trang.

### UI tasks

- [ ] Tạo trang `/documents` với danh sách, trạng thái, tên file và metadata có sẵn.
- [ ] Tạo upload dropzone desktop + button chọn file; mobile dùng native file picker.
- [ ] Validate kích thước/extension ở frontend để UX nhanh, nhưng backend vẫn là nguồn quyết định.
- [ ] Hiển thị queued/processing/ready/failed; chỉ hiển thị stage nếu backend thật sự trả stage.
- [ ] Retry chỉ xuất hiện khi thao tác retry được backend hỗ trợ và an toàn.
- [ ] Double-click/re-render không được tạo nhiều upload không chủ ý.
- [ ] Empty state hướng dẫn upload; failed state nêu lỗi có thể hành động.
- [ ] Không hiển thị phần trăm tự tính từ thời gian hoặc số request model.

### Tests

- PDF hợp lệ, PDF hỏng/blank, MIME giả, file quá giới hạn, duplicate upload, parser/embedding failure, ownership mismatch, status transition, cleanup file tạm và restart khi đang xử lý.

### Điều kiện nghiệm thu

Upload PDF → backend xử lý → document READY/FAILED → UI cập nhật bằng trạng thái thật. User A không thể xem metadata/status của User B. Không đổi Chroma layout/vector dimension.

## 12. Phase 5 — AI Tutor và citations

**Commit gợi ý:** `feat(web): add document tutor with evidence citations`

### API tasks

- [ ] Tạo chat endpoint dựa trên `AnswerQuestionUseCase`/session facade đã có; không port ReAct/RAG logic sang TypeScript.
- [ ] Mỗi request authorize document trước khi retrieval.
- [ ] Chuẩn hóa response DTO: answer, citations/evidence, request/run ID và metadata an toàn cần cho UI.
- [ ] Citation tối thiểu: document ID/title, chunk ID, snippet/text, page bounds nếu có, optional score; không bịa page number.
- [ ] Chốt synchronous response hay SSE. Nếu SSE: event type/schema, sequence/event ID, heartbeat, reconnect, cancel, disconnect cleanup và error event phải được test.
- [ ] Empty retrieval không được gọi LLM để bịa nguồn; UI phải giải thích rằng chưa tìm thấy ngữ cảnh phù hợp.
- [ ] Map provider/quota failure thành 429/503 hoặc error contract đã chốt.

### UI tasks

- [ ] Tạo route `/documents/[documentId]/study`.
- [ ] Desktop: reader + tutor panes, có thể collapse; không ép thành 3 cột.
- [ ] Mobile: tab **Đọc / Hỏi AI**, giữ draft/context khi chuyển tab.
- [ ] Chat composer có pending/streaming/reconnecting/disabled/quota state.
- [ ] Citation chips có thể mở viewer/bottom sheet với source, trang và snippet.
- [ ] Agent activity chỉ hiển thị status an toàn: retrieval, kiểm tra nguồn, soạn trả lời.
- [ ] Giữ input và scroll position hợp lý; không auto-scroll làm mất đoạn PDF đang đọc.
- [ ] Khi document bị xóa/không còn quyền, đóng session và báo rõ.

### Điều kiện nghiệm thu

Vertical slice đầu tiên phải chạy thật: login → upload PDF → READY → hỏi AI → nhận answer → mở citation đúng tài liệu/trang nếu có. Citation UI chỉ render evidence backend trả về. Test empty retrieval, provider error, timeout/disconnect và cross-user document ID.

## 13. Phase 6 — Quiz, progress và learning path

**Commit gợi ý:** `feat(web): add quiz and learning progress flows`

### Quiz

- [ ] Map GenerateQuizUseCase/learning session sang typed DTO; không trả quiz dưới dạng text để frontend parse regex.
- [ ] Validate schema: đúng 4 lựa chọn, một correct index hợp lệ, explanation có thể rỗng.
- [ ] Không gửi correct answer về client trước khi submit nếu UX yêu cầu đánh giá độc lập.
- [ ] Submit attempt qua use case hiện có; authorize document và validate selected index ở backend.
- [ ] Chốt idempotency/double-submit để progress không tăng hai lần ngoài policy.
- [ ] Mỗi màn hình mobile chỉ hiển thị một câu; có x/N, 4 option lớn, feedback và explanation sau submit.
- [ ] Nếu quiz history vẫn chỉ là session state, ghi rõ; không hiển thị “Lịch sử” như dữ liệu bền vững.

### Progress và learning path

- [ ] Dùng `GetProgressUseCase`/repository hiện có; kiểm tra mọi query được scope theo principal.
- [ ] Phân biệt điểm quiz, mastery ước tính và nội dung đã hoàn thành; không gộp thành một phần trăm vô nghĩa.
- [ ] Learning path mặc định là list-first; graph chỉ là toggle tùy chọn.
- [ ] Graph rỗng hoặc có cycle phải có fallback list/empty state.
- [ ] Nếu persistence cho notes/history chưa đủ, defer feature thay vì tạo UI giả.
- [ ] Chỉ hiển thị recommendation khi có dữ liệu/provenance backend; không hard-code “AI đề xuất” cho fixture.

### Điều kiện nghiệm thu

Quiz generation, submit, explanation và progress hoạt động end-to-end. Tests chứng minh ownership, validation, provider failure, submit lặp và graph empty/cycle. Feature nào chưa có backend support phải được ghi defer.

## 14. Phase 7 — Hoàn thiện mobile, accessibility và design fidelity

**Commit gợi ý:** `fix(web): harden responsive learning flows`

Kiểm thử tối thiểu tại các viewport:

- 360×800 — điện thoại nhỏ.
- 390×844 — điện thoại phổ biến.
- 768×1024 — tablet.
- 1024×768 — laptop hẹp.
- 1280×800 và 1440×900 — desktop.

Checklist:

- [ ] Không horizontal overflow ở body.
- [ ] Bottom nav/composer/CTA không bị che bởi keyboard hoặc safe area.
- [ ] Mọi action quan trọng dùng được bằng touch và keyboard.
- [ ] Focus order hợp lý; focus ring rõ; icon-only button có accessible name.
- [ ] Form error và job/chat status được thông báo phù hợp cho screen reader.
- [ ] Không chỉ dùng màu để phân biệt đúng/sai/status.
- [ ] Dialog/sheet quản lý focus và đóng bằng Escape khi phù hợp.
- [ ] Reduced motion được tôn trọng.
- [ ] Loading skeleton không làm layout nhảy quá mạnh.
- [ ] Citation sheet và quiz options không quá chật trên phone.
- [ ] So sánh screenshot với sketch; mọi sai lệch lớn được ghi nhận và xử lý, không chỉ “trông ổn”.

Dùng Playwright cho luồng chính và axe/accessibility checks nếu đã cấu hình. Tự động test không thay thế việc kiểm tra thao tác bằng điện thoại thật.

## 15. Phase 8 — Docker, CI, cutover và gỡ Streamlit

**Commit gợi ý:** `chore(deploy): cut over from Streamlit to web and API`

Chỉ mở phase này khi Phase 2–7 đã merge/test trong nhánh và regression matrix đạt.

### Compose/runtime

- [ ] Tạo production Dockerfile riêng cho `apps/api` và `apps/web`; build reproducible và chạy non-root khi khả thi.
- [ ] Cập nhật `compose.yaml` thành web/api/db/migrate; giữ local-ai/Ollama profile nếu còn dùng.
- [ ] Không thay tên/volume `postgres_data`, `app_data`, `hf_cache` hoặc Chroma path khi chưa rehearsal.
- [ ] Chuyển healthcheck khỏi `/_stcore/health` sang API/web health endpoint phù hợp.
- [ ] Chỉ expose web port ra host; DB và API ở internal network trừ khi có quyết định expose API riêng.
- [ ] Kiểm tra Alembic chạy trước API nhận traffic.
- [ ] Cập nhật `config/docker.env.example`, docs vận hành, README và troubleshooting.
- [ ] Test shutdown/restart và log không chứa secrets/document content.

### CI

- [ ] Giữ Python offline/unit/contract job hiện có.
- [ ] Giữ PostgreSQL integration/migration job.
- [ ] Thêm frontend lint, typecheck, unit test và production build.
- [ ] Thêm API tests và OpenAPI consistency check.
- [ ] Thêm Docker Compose smoke test cho web/API/DB/migration.
- [ ] CI mặc định không yêu cầu cloud credentials hoặc download model lớn.
- [ ] Chỉ gỡ Streamlit smoke/AppTest, dependency và config khi không còn dùng để kiểm chứng sản phẩm chính.

### Data cutover / rollback

- [ ] Backup PostgreSQL và app/Chroma data.
- [ ] Restore thử trên môi trường test.
- [ ] Chạy smoke login → upload → chat/citations → quiz/progress với dữ liệu synthetic.
- [ ] Kiểm tra dữ liệu cũ đọc được; không reset DB/Chroma.
- [ ] Giữ image/Compose cũ để rollback.
- [ ] Thử rollback bằng cách chuyển traffic về phiên bản cũ trên môi trường test.
- [ ] Sau khi ổn định mới xóa `apps/streamlit_legacy`, `.streamlit`, Streamlit dependencies/config và docs cũ.
- [ ] Không merge chỉ vì giao diện mới đẹp; phải đạt tất cả gate dữ liệu/security/CI.

## 16. API contract và error handling dùng thống nhất

Các endpoint dưới đây là **đề xuất** cần map sang use case và chốt trong OpenAPI trước khi implementation. Không coi chúng là route đang chạy.

| Capability | Route dự kiến | Quy tắc |
|---|---|---|
| Health | `GET /health/live`, `GET /health/ready` | Tách liveness/readiness |
| Auth | `POST /api/v1/auth/register`, `login`, `logout`, `GET /api/v1/auth/me` | Principal lấy từ session |
| Documents | `GET /api/v1/documents`, `POST /api/v1/documents`, `GET /api/v1/documents/{id}` | Ownership bắt buộc |
| Ingestion | `GET /api/v1/documents/{id}/status` hoặc job route đã chốt | Status thật; không giả progress |
| Chat | `POST /api/v1/documents/{id}/chat` | Evidence/citations có schema |
| Quiz | `POST /api/v1/documents/{id}/quizzes`, `POST /api/v1/quiz-attempts` | Typed schema, ownership, double-submit policy |
| Progress | `GET /api/v1/progress` | Chỉ dữ liệu của principal |
| Learning path | `GET /api/v1/documents/{id}/learning-path` | Chỉ bật khi capability được map/test |

Error contract phải ổn định và không phụ thuộc vào câu chữ:

- 400/422: request/file sai; trả field/code có thể hành động.
- 401: chưa xác thực/session hết hạn.
- 404 (hoặc 403 theo ADR): resource không có hoặc không thuộc user; tránh document enumeration.
- 409: conflict/idempotency nếu semantics phù hợp.
- 429: quota/rate limit; kèm retry guidance khi có thể.
- 503: provider/dependency tạm thời không khả dụng.
- 500: lỗi không mong đợi; trả request ID, không trả stack trace.

DTO frontend phải được generate/validate từ OpenAPI hoặc được kiểm tra contract. Không duy trì schema frontend và backend bằng cách copy-paste rồi hy vọng chúng khớp.

## 17. Test matrix phải chạy trước khi kết thúc mỗi phase

| Case | Kết quả bắt buộc |
|---|---|
| Chưa login gọi protected API | 401 |
| User A đọc document của User B | Không tiết lộ document; 404/403 theo ADR |
| Logout rồi back/reload | Không còn dữ liệu account trước trong UI/query cache |
| Upload PDF hỏng/quá giới hạn | Bị từ chối an toàn; không tạo record/file rác ngoài kiểm soát |
| Embedding/provider fail | FAILED/error state rõ; không spinner vô hạn |
| Upload trùng nội dung | Dedupe theo semantics hiện có |
| Retrieval rỗng | Không gọi LLM để tạo câu trả lời có nguồn giả |
| Citation không có page number | Hiển thị nguồn mà không bịa trang |
| Provider quota/unavailable | Error state ổn định; không lộ key |
| Quiz payload thiếu/option sai | Backend reject; UI không tự chấm bằng dữ liệu lỗi |
| Double-submit quiz | Không ghi progress hai lần ngoài policy |
| Graph rỗng/cycle | Fallback an toàn |
| API restart lúc ingestion chạy | Theo recovery policy đã chốt; không để processing vô hạn |
| DB/Chroma volume cũ | Dữ liệu cũ đọc được sau cutover rehearsal |
| Web/API dependency unavailable | Readiness/error UI phản ánh đúng tình trạng |

## 18. Cách làm việc trong nhánh này

### Commit theo checkpoint

Tạo commit nhỏ sau mỗi mục tiêu chạy được. Ví dụ:

1. `docs(ui): add implementation playbook and sketch references`
2. `feat(web): scaffold Next.js app and design tokens`
3. `feat(web): add responsive navigation shell`
4. `feat(api): add FastAPI health and app lifespan`
5. `feat(api): add session authentication`
6. `feat(web): integrate login and session expiry`
7. `feat(api): expose owned document list and upload`
8. `feat(web): add document library and status polling`
9. `feat(api): expose grounded chat evidence`
10. `feat(web): add AI tutor and citation viewer`
11. `feat(web): add quiz and progress`
12. `test(e2e): cover first complete learning flow`
13. `chore(deploy): add web and API Compose services`
14. `chore(ui): remove Streamlit after cutover gates pass`

Không bắt buộc dùng đúng tên commit, nhưng giữ mỗi commit có thể review/rollback riêng.

### Sau mỗi checkpoint

Chạy các kiểm tra tương ứng:

```powershell
# Python/core regression
.venv/Scripts/python -m pytest -q
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/python scripts/check_import_boundaries.py

# Frontend — chạy trong apps/web
npm run lint
npm run typecheck
npm run test
npm run build
```

Chạy những script frontend đã được khai báo thật trong `package.json`. Nếu test chưa được cấu hình, thêm test runner và test trước khi tuyên bố phase đã pass.

### PR description nên có

- Scope / non-goals.
- Screenshot desktop + mobile đối chiếu sketch.
- API/OpenAPI changes.
- Security/ownership impact.
- DB/Chroma/volume impact.
- Tests run và kết quả.
- Known limitations/deferred items.
- Rollback note.

## 19. Definition of Done cho nhánh implementation

Không coi nhánh đã hoàn tất cho đến khi:

- [ ] Sketch assets và design reference được version-control hoặc liên kết rõ trong repository.
- [ ] Next.js UI có routes và states cho các capability đã duyệt.
- [ ] FastAPI chạy thật, OpenAPI phản ánh runtime và auth/ownership được test.
- [ ] UI không dùng mock cho luồng được tuyên bố là hoàn thành.
- [ ] Upload → processing → ready → chat → citation thật chạy end-to-end.
- [ ] Quiz submit/progress hoạt động theo semantics persistence đã công bố.
- [ ] Desktop/mobile đã được kiểm thử; không có critical usability/accessibility blocker.
- [ ] Core tests độc lập UI vẫn xanh.
- [ ] Compose, healthcheck và CI không phụ thuộc Streamlit trước khi gỡ Streamlit.
- [ ] Backup/restore và rollback rehearsal hoàn tất.
- [ ] README, env examples, API docs và architecture docs được cập nhật.
- [ ] Mọi capability chưa có backend support được ghi rõ, không được giả lập là đã hoàn thành.

## 20. Bắt đầu ngay — checklist đầu tiên

Thực hiện theo đúng thứ tự này, chưa cần code API/UI ngay:

1. [ ] Checkout `feature/ui-learning-workspace`.
2. [ ] Chạy baseline Python tests/lint/import-boundary; ghi lại kết quả.
3. [ ] Copy sketch desktop/mobile vào `docs/design/ui-v1/assets/` và thêm design master plan nếu muốn version-control.
4. [ ] Review `FRONTEND_MIGRATION_NEXTJS_FASTAPI.md` và tài liệu này; quyết định Course domain cho MVP.
5. [ ] Tạo route inventory + feature parity matrix từ `apps/streamlit_legacy`.
6. [ ] Chốt ADR auth/session và ingestion job/status.
7. [ ] Freeze OpenAPI MVP cho auth, documents/status và chat/citations.
8. [ ] Tạo commit tài liệu, sau đó mới scaffold Next.js.
9. [ ] Không xóa hoặc sửa sâu Streamlit cho đến khi có vertical slice thay thế đã qua regression.

**Lựa chọn MVP được khuyến nghị:** ưu tiên hoàn thiện một luồng document-first có giá trị thật trước; chỉ thêm Course persistence khi quyết định đó được chốt bằng ADR. Đây là cách giảm scope và rủi ro cho một nhánh tự triển khai, đồng thời vẫn giữ hướng thiết kế Personalized AI Learning Workspace.
