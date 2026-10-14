# SELF STUDY SUPPORTER — UI/UX MASTER PLAN v1.0.0

> Tài liệu định hướng thiết kế và triển khai UI cho **Personalized AI Learning Agent**  
> Ngày: 13/10/2026 · Repository: https://github.com/ManhT005/self-study_supporter · Baseline nhánh `main`, commit `cb67b95d890fc90eff98df1960d68384e48c99b7` (23/08/2026).  
> Trạng thái: **ĐỀ XUẤT/THIẾT KẾ**, chưa sửa code, chưa triển khai Figma production, chưa chạy E2E.

---

## 1. Quyết định sản phẩm

**Từ:** Streamlit app với 4 tab Tổng quan / Trợ lý / Lộ trình / Quiz, một sidebar đa nhiệm chứa upload PDF, model, nguồn tài liệu và Thought Log.  
**Đến:** Personalized AI Study Workspace: người học được dẫn dắt qua 1 vòng khép kín **Chọn mục tiêu → Nạp tài liệu → Học có dẫn chứng → Kiểm tra → Phát hiện điểm yếu → Ôn tập → Cập nhật kế hoạch**.

**Định vị:** Không cố clone ChatGPT, Notion hay LMS tổng quát. Đây là một trợ lý học tập có tài liệu riêng, biết người học đang ở đâu, có tác vụ rõ ràng và đánh giá được tiến bộ.

### North-star experience

1. Khi đăng nhập, người học thấy **bước học tiếp theo**, không thấy một màn hình cấu hình model.
2. Mỗi môn học có **workspace riêng**, tài liệu, graph, quiz, history và tiến độ tách biệt.
3. AI câu trả lời có **citation thật** và gợi ý bước tiếp theo; thiếu bằng chứng phải nói rõ.
4. Sau một bài quiz, người học biết **sai concept nào** và có CTA để học lại.
5. UI phải dễ dùng bằng điện thoại: không chuyển 3 cột desktop thành 3 cột bé.

## 2. Audit thiết kế/code: ưu tiên khắc phục

| ID | Hiện trạng đã kiểm tra | Đường dẫn | Hậu quả UX | Đề xuất |
|---|---|---|---|---|
| UX-01 | CSS lớn nhúng trong `main.py` và dùng selector toàn cục `!important` | `main.py` | Khó maintain; nút/chữ/theme thiếu nhất quán | Design tokens + component styles; không lạm dụng `!important` |
| UX-02 | 4 nút điều hướng đặt ngang ở mọi kích thước | `ui/router.py` | Trên mobile chật, thao tác khó | Desktop: sidebar; mobile: bottom nav |
| UX-03 | Model selector, upload, nguồn và Thought log chen trong sidebar | `ui/components/sidebar.py` | Không gian học bị thu hẹp; gây phân tâm | Sidebar chỉ chứa navigation; model trong Settings/Advanced; source theo câu trả lời |
| UX-04 | Ingestion (parse/embed/graph) chạy trong UI function | `ui/components/sidebar.py` | UI chờ, khó resume/đóng tab, trạng thái nhảy | API + background job + progress events |
| UX-05 | “Sources” hiển thị cả nhãn giả định như Knowledge Graph/Progress Notes | `ui/components/chat.py` | Dễ tạo hiểu lầm về dẫn chứng | Chỉ render `Citation[]` từ backend; mở được đúng PDF/trang/chunk |
| UX-06 | Chat không hiển thị task lifecycle của Agent một cách an toàn | `ui/components/chat.py`, `src/agent/orchestrator.py` | User không biết đang search, re-rank hay đợi model | Hiển thị activity timeline tóm tắt, **không** raw chain-of-thought |
| UX-07 | Quiz được parse lại bằng regex từ text | `ui/components/quiz_arena.py` | Có thể chấm sai; lỗi định dạng | Backend trả JSON có schema; UI nhận typed payload |
| UX-08 | Lộ trình hiển thị theo expander tuyến tính | `ui/components/graph_viewer.py` | Khó phân biệt prerequisite, tiến độ và nội dung kế tiếp | Course map: list-first + graph toggle, trạng thái mastery |
| UX-09 | Nhiều trạng thái phiên xử lý chung trong `st.session_state` | `main.py`, `ui/*` | Dễ mất context/khó kiểm soát khi đổi môn hay tài khoản | `course_id`, `document_id`, `session_id` explicit; cache theo scope |
| UX-10 | UI giới thiệu nhiều khả năng nhưng không đi từ việc học hôm nay | `ui/router.py` | Trải nghiệm giống demo tính năng | Dashboard contextual: Next action / Review due / Continue |

**P0 bảo mật song hành:** bỏ log DATABASE_URL ở `main.py`; xóa hoàn toàn auth/session-sensitive state lúc logout; kiểm tra ownership trên backend; escape/sanitize văn bản từ LLM và tài liệu; không đưa bí mật/model logs vào UI.

## 3. Persona và Jobs To Be Done

- **Sinh viên học theo học phần:** "Tôi cần biết hôm nay nên học chương nào và đang yếu phần gì." → Dashboard + Learning Plan.
- **Sinh viên ôn thi gấp:** "Tôi muốn tổng hợp nhanh nội dung giáo trình và luyện câu hỏi trọng tâm." → Course + Practice + review.
- **Người tự học kiến thức mới:** "Tôi cần trợ giảng giải thích từ dễ đến khó và có dẫn chứng." → Tutor + evidence + hint mode.
- **Người dùng mobile:** "Tôi có 10 phút rảnh và muốn ôn một vài thẻ hoặc làm quiz." → Mobile short session, single-primary-action.

### Các nguyên tắc bắt buộc

- **Learning-first**: hiển thị việc cần làm trước các cấu hình kỹ thuật.
- **One primary action per view**: một CTA nổi bật, hành động phụ rõ thứ bậc.
- **Evidence-based AI**: phản hồi có nguồn, tình trạng nguồn và nút mở tài liệu.
- **Agent with boundaries**: AI **đề xuất** tạo lịch/ghi chú và xin duyệt khi thay đổi dữ liệu quan trọng.
- **Progress over gamification**: giải thích mức tiến bộ trước điểm thưởng/streak.
- **Explainable, not raw reasoning**: hiển thị bước đang chạy và bằng chứng, không hiển thị suy luận nội bộ thô.
- **Accessible & responsive**: keyboard/focus/ARIA, contrast, reduced-motion, touch targets; mục tiêu WCAG 2.2 AA.

## 4. Information Architecture (IA)

### Điều hướng desktop (global)

1. **Hôm nay** (`/dashboard`) — lịch hôm nay, review due, tiếp tục buổi học.
2. **Môn học** (`/courses`) — tất cả workspace môn, tìm/chọn môn.
3. **Luyện tập** (`/practice`) — quiz, flashcard, các bài ôn đến hạn.
4. **Tiến độ** (`/progress`) — mastery, hoạt động, mục tiêu.
5. **Trợ giảng AI** (`/tutor`) — phiên chat gần nhất; chọn môn/source context.
6. **Cài đặt** (`/settings`) — hồ sơ, privacy/memory, provider (Advanced), accessibility.

Trong `/courses/:courseId` có **secondary navigation**: `Tổng quan` / `Tài liệu` / `Lộ trình` / `Học cùng AI` / `Quiz`; breadcrumb rõ môn → chương/tài liệu. Không hiển thị các menu môn khác trong sidebar cấp 2.

### Navigation mobile

Bottom nav 4 mục: `Hôm nay` / `Môn học` / `Luyện tập` / `Tiến độ`. AI Tutor mở qua CTA trong course hoặc floating action có nhãn rõ. `Cài đặt` ở avatar. Không dùng horizontal nav đầy đủ của desktop.

## 5. Mô tả sketch và screen contracts

### S01 — Dashboard (`/dashboard`)

**Above the fold:** lời chào nhẹ + current course + nút **Tiếp tục học**. Section ưu tiên: (A) Việc nên làm hôm nay; (B) Ôn tập đến hạn; (C) Môn học gần đây; (D) Gợi ý AI có nguồn nguyên nhân (“Bạn sai 3 câu Queue gần nhất”). Không dùng giả dữ liệu khi backend thiếu — render empty state.

**UI:** summary metrics 2–4 thẻ; progress card nhỏ; recent courses; agenda 3 items max trước khi "Xem tất cả".

**States:** first-time onboarding / returning user / no courses / due review / loading / offline / no personalized recommendation.

### S02 — Course Workspace (`/courses/:courseId`)

Header course + mục tiêu + trạng thái ingest. Tabs: Overview, Materials, Learning path, Study/Chat, Practice. Cho phép chuyển tài liệu mà không làm mất câu hỏi đang gõ. Hiển thị “Dùng nguồn: X tài liệu” với chọn rõ scope.

### S03 — AI Tutor / Focus Reading (`/courses/:courseId/study`)

**Desktop:** chế độ split ~58% **Document Reader** / 42% **Tutor**, collapse được bất kỳ pane; không ép sidebar thứ ba. Reader: TOC, zoom, highlighter, selected text → menu `Giải thích / Tạo flashcard / Ghi chú`. Tutor: modes `Giải thích`, `Gợi ý`, `Hỏi đáp`, `Kiểm tra nhanh`; input sticky; evidence chips hiển thị tên tài liệu và trang. Nút `Đề xuất đưa vào lộ trình` chỉ gửi đề xuất, phải người học xác nhận.

**Mobile:** chuyển thành single-pane `Đọc` ↔ `Hỏi AI`; citations mở bằng bottom sheet (tên nguồn, trang, đoạn trích, `Mở trang`); input ở cuối trang; không làm mất context khi chuyển pane.

**Agent activity:** “Đang tìm trong 2 tài liệu”, “Đang kiểm tra nguồn”, “Đang soạn câu trả lời”; không xuất `Thought:` hoặc hidden reasoning; sau khi hoàn tất ẩn activity dài và có thể mở "Chi tiết thực thi" ở mức công cụ/nguồn.

**States:** chưa chọn môn, chưa tài liệu, indexing, retrieval empty, no citation, streaming, cancelled, quota exhausted, provider degraded, model offline, regenerate, handoff.

### S04 — Knowledge & Learning Path (`/courses/:courseId/path`)

Default: **list-first** (Chương → concept → trạng thái `Chưa học/Đang học/Cần ôn/Đã vững`), vì dễ thao tác mobile và accessibility. Toggle optional `Xem sơ đồ` dùng graph có pan/zoom và fallback list. Show prerequisite cảnh báo, progress, next action. Không hiển thị topological sort như một bảo đảm “tối ưu” nếu chưa có mastery/time data.

### S05 — Practice & Quiz (`/practice` và trong course)

Tab: `Quiz` / `Flashcard` / `Ôn tập` / `Lịch sử`. Setup chỉ 3 lựa chọn quan trọng: môn/chủ đề, số lượng câu, mức độ; advanced tùy chọn nguồn. Trong quiz: một câu mỗi màn, progress x/N, câu hỏi và 4 option lớn, submit → explanation + evidence + `Học lại khái niệm`; sau hoàn thành: điểm, lỗi theo concept, due reviews, CTA `Ôn tập phần yếu`. Khi nguồn không đủ để sinh câu đáng tin cậy, báo lý do, không sinh đáp án giả.

### S06 — Materials Library (`/courses/:courseId/materials`)

Card/table responsive: filename, type, pages, uploaded_at, processing status (Queued, Parsing, Chunking, Embedding, Indexing, Ready, Failed), job progress không lùi/nhảy vô lý, retry và lỗi rõ. Drag-drop upload desktop có button alternative; mobile native picker. Upload scan PDF show OCR needed and fallback; multi-file support chỉ khi backend hỗ trợ.

### S07 — Progress (`/progress`)

Mastery theo course/concept, timeline 7/30 ngày, bảng các concept cần ôn, lịch học vs thực tế. Phân biệt `Điểm quiz`, `Mức độ thành thạo ước tính` và `Hoàn thành nội dung`; tuyệt đối không cộng gộp các metrics thành một số phần trăm vô nghĩa.

### S08 — Onboarding (`/welcome`)

3 bước có thể skip: (1) mục tiêu môn học, (2) quỹ thời gian học, (3) thêm tài liệu hoặc thử nội dung mẫu có ghi “demo”. Sau đó dẫn đến `Tiếp tục học` / `Bắt đầu học` thay vì chỉ tới màn hình upload.

### S09 — Settings / Trust

Quản lý hồ sơ, tùy chọn hiển thị, quản lý/khóa/xóa memory, quyền sử dụng tài liệu. Provider/model ở tab **Nâng cao** (ưu tiên cho self-host) tách biệt khỏi người học. Khóa, token, raw log chỉ ở server và hệ thống cấu hình phù hợp.

## 6. Responsive / Layout specifications

| Viewport | Quy tắc layout | Interaction |
|---|---|---|
| Desktop ≥1280px | Global nav 224–248px; content max 1440px; Reader+Tutor split ~58/42 | Sidebar persistent; right pane resize/collapse |
| Laptop 1024–1279 | Nav icon rail 64–72px hoặc collapsible 224px; reader/tutor split 55/45 | Hạn chế banner/card chiều ngang |
| Tablet 768–1023 | Nav drawer; một vùng primary + panel dạng overlay hoặc tab | Không ép 3 cột |
| Phone 360–767 | Single column, bottom nav, sticky composer/CTA, bottom sheets | Min touch target đề xuất 44×44 CSS px |

**WCAG 2.2 AA:** chuẩn target size minimum 24×24 CSS px hoặc các ngoại lệ theo WCAG; sản phẩm chủ động dùng ≥44×44px cho vùng bấm mobile. Font body 15–16px, line height ~1.5; keyboard Tab/Enter/Space hoạt động; focus ring rõ; labels không chỉ icon; skeleton có accessible name; screen reader có cập nhật status theo ngữ cảnh. Tránh auto-scroll nếu người học đang đọc nguồn hoặc đang review câu trả lời.

### Design tokens (đề xuất)

```css
:root {
  --brand-600: #2563eb;       /* Primary actions */
  --brand-700: #1d4ed8;
  --ink-900: #0f172a;
  --ink-600: #475569;
  --surface-0: #ffffff;
  --surface-50: #f8fafc;
  --border-200: #e2e8f0;
  --success-600: #059669;
  --warning-600: #d97706;
  --danger-600: #dc2626;
  --radius-card: 16px;
  --radius-control: 10px;
  --space-unit: 4px;
}
```

Cấm dùng màu đơn lẻ để biểu thị đáp án đúng/sai/trạng thái ingestion; luôn đi kèm icon và text. Các thiết kế đầu tiên ưu tiên light theme; dark mode sau khi có token/theme system chuẩn.

## 7. Component inventory (Figma và frontend)

**Primitives:** Button, IconButton, Input, Textarea, Select, Combobox, Tabs, Dialog, Sheet, Dropdown, Tooltip, Badge, Progress, Skeleton, Toast, EmptyState, ErrorState, Breadcrumb.

**Learning domain:** CourseCard, NextStudyCard, ReviewDueCard, TopicMasteryRow, StudyPlanTimeline, ConceptPrerequisiteTag, CitationChip, CitationViewerSheet, DocumentViewer, SourceSelector, AgentActivityStepper, ChatComposer, SuggestedPromptChips, QuizQuestionCard, QuizFeedback, Flashcard, UploadJobCard, ProviderAvailability.

**Cross-cutting:** NavigationShell, GlobalSidebar, CourseSidebar, MobileBottomNav, CourseSwitcher, ErrorBoundary, ReconnectBanner, ConfirmationDialog, AccessibleMarkdown.

### Component state matrix

| Component | States cần thiết |
|---|---|
| ChatComposer | empty, typing, submitting, streaming, reconnecting, disabled, quota |
| CitationChip | available, loading preview, removed document, permission denied |
| UploadJobCard | queued, parsing, embedding, indexing, ready, failed, retrying, cancelled |
| QuizQuestion | unanswered, selected, submitted-correct, submitted-incorrect, error |
| StudyPlanCard | proposed, pending approval, accepted, changed, completed |
| AgentActivity | queued, running, needs approval, complete, failed, cancelled |

## 8. UX flows bắt buộc

### Flow A: New user

`Signup → Goal/time setup → Create course → Upload or demo → Ingestion status → AI-generated outline preview → Confirm/create plan → First learning session`.

### Flow B: Study with PDF

`Open course → Choose document → Select text → Ask AI → Stream answer → Click citation → Source highlight → Continue/Make flashcard`.

### Flow C: Weak concepts

`Finish quiz → Explain wrong answers → Record attempt → Update mastery → Suggested remedial lesson → Accept update learning plan → Schedule review`.

### Flow D: Error recovery

`Upload failed → show stage/error, job ID and retry → retry safe/idempotent → finished → notify`; `quota exhausted → retry later/change provider (advanced)`, not blank spinner.

### Flow E: Privacy

`Open memory → inspect entry/source/date → edit/delete with confirmation → verify server-side ownership and removal`.

## 9. Frontend ↔ API ↔ LangGraph interaction contract

### Recommended stack for production v1.0.0

- **Web UI:** Next.js App Router + TypeScript + Tailwind + shadcn/ui (or React + Vite if minimizing hosting complexity is more important than route/SSR). **Choose one; do not maintain two production frontends.**
- **Frontend quality:** TanStack Query for server state, Zod schema validation, component tests (Vitest + Testing Library), Playwright E2E, axe accessibility checks.
- **Backend:** FastAPI applications; LangGraph orchestration; existing AI Core through pure interfaces; background worker for ingest/expensive jobs; relational DB and vector store.
- **Streamlit:** keep as optional developer/eval playground during migration, not end-user production interface once Next.js becomes primary.

### Suggested endpoints — new contracts, not implemented yet

```text
GET    /api/me
GET    /api/dashboard
GET    /api/courses
POST   /api/courses
GET    /api/courses/{course_id}
GET    /api/courses/{course_id}/documents
POST   /api/courses/{course_id}/documents       -> 202 + job_id
GET    /api/jobs/{job_id}
POST   /api/jobs/{job_id}/retry
GET    /api/courses/{course_id}/learning-path
POST   /api/courses/{course_id}/learning-plan/proposals
POST   /api/learning-plan/proposals/{id}/accept
POST   /api/tutor/sessions
POST   /api/tutor/sessions/{id}/messages
GET    /api/tutor/runs/{run_id}/events            -> typed SSE
POST   /api/tutor/runs/{run_id}/cancel
POST   /api/quiz/generate
POST   /api/quiz/attempts
GET    /api/progress?course_id=...
GET    /api/me/memories
DELETE /api/me/memories/{memory_id}
```

### SSE event schema (minimized and user-safe)

```json
{
  "event_id": "evt_0001",
  "run_id": "run_123",
  "course_id": "course_1",
  "type": "retrieval.started",
  "timestamp": "2026-10-13T10:00:00Z",
  "payload": {
    "label": "Đang tìm bằng chứng trong tài liệu",
    "source_count": 2
  }
}
```

Event types: `run.started`, `retrieval.started`, `retrieval.completed`, `answer.delta`, `citation.added`, `approval.required`, `run.completed`, `run.failed`, `run.cancelled`. Event cần `run_id`, monotonic sequence/event ID, reconnect strategy, và idempotent reducer. UI chỉ dùng event được backend xác định an toàn để hiển thị; **không dùng raw chain-of-thought**.

**Citation contract:** `citation_id`, `document_id`, `document_title`, `page_start`, `page_end`, `chunk_id`, `snippet`, optional `highlight_bounds`, `viewer_url` do server cấp; mọi endpoint kiểm tra ownership theo user/course.

**Background ingestion:** UI không suy ra % từ số request LLM. Server phát `stage`, `processed`, `total`, `percent` có monotonic semantics theo một `job_id`; retry phải có `attempt_id` và trạng thái rõ, không giật lùi % trên cùng attempt.

### Contract ownership

- Frontend sở hữu presentation state (tabs, sheets, unsent drafts).
- Backend sở hữu authz, data persistence, evidence metadata, quiz answers, progress, job statuses.
- LangGraph sở hữu graph execution/checkpoint, **không** thay thế cơ sở dữ liệu nghiệp vụ.
- UI không gọi thẳng Ollama/Provider APIs hay lưu API keys trong localStorage.

## 10. Migration strategy không làm gián đoạn AI Core

1. **Snapshot baseline:** lưu lại UI flows, screenshots, test smoke; bảo đảm có Docker env và sample data.
2. **Contract-first:** Pydantic response schemas + OpenAPI + generated TypeScript client; tập trung ownership.
3. **Backend adapter:** expose use cases hiện có qua FastAPI, thay vì copy logic Streamlit sang TS.
4. **New web shell:** auth, sidebar, course switcher, dashboard, empty states bằng mock data.
5. **Vertical slice đầu tiên:** Course → Document upload → Ready → Tutor chat → grounded citation → Quiz result.
6. **Feature parity:** graph, progress, provider advanced settings, history.
7. **Cutover:** E2E gates xanh, staging review, QA mobile; đánh dấu Streamlit là dev-only.

### Không làm trong đợt UI đầu tiên

- Social feed, marketplace tài liệu, gamification phức tạp, collaborative realtime, course authoring LMS đầy đủ.
- Multi-agent avatars/icon animation nặng; hiển thị raw Thought log; fine-tuning chỉ để giao diện “thông minh”.
- Figma thiết kế 25 trang trước khi xác nhận 5 flow cốt lõi có chạy thật hay không.

## 11. Execution roadmap — 6 phases

| Phase | Nội dung | Deliverables | Definition of Done |
|---|---|---|---|
| U0 — Audit + Freeze | User flow, UI defects, API boundaries, sample dataset | IA, backlog, page inventory, contract drafts | PM/Tech lead chốt scope, có baseline screenshot |
| U1 — Design system + Sketch | Tokens, components, responsive patterns, hi-fi for 5 core screens | Figma-ready specs, exported desktop/mobile, state matrix | 5 screens + loading/error/empty/approval và accessibility review |
| U2 — Shell + Auth/Courses | Next.js app shell, auth, navigation, course switching | Dashboard/Courses responsive | Mobile bottom nav, scoped routes, logout clean |
| U3 — Study + AI Tutor | Document reader, sources, typed streaming, uploads | AI Tutor 2-pane, mobile split-to-tabs, Citation Viewer | Verify grounded citations, resuming, errors |
| U4 — Practice + Path | Quiz JSON, source validation, flashcards, path | Practice flow, Graph/list view, results | No incorrect default answer, progress correctly stored |
| U5 — Personalization | Learning agenda, mastery, review due, plan approval | Dashboard recommendations + Progress | Recommendation provenance, consent for writes |
| U6 — Hardening + Release | QA, tests, telemetry, performance, security | CI + release checklist + UX evidence | E2E pass, WCAG critical issues closed, mobile QA complete |

**Ước lượng thô:** 6–10 tuần cho 2 người có sẵn AI/backend, tùy mức sẵn sàng API và mức độ hoàn thiện learning logic. Tách branch theo phase, tránh PR chứa toàn bộ UI + RAG + LangGraph.

### Suggested branches

```text
feature/ui-ux-design-system
feature/ui-shell-courses
feature/ui-tutor-citations
feature/ui-practice-learning-path
feature/ui-personalization-dashboard
fix/ui-accessibility-mobile
release/v1-ui-hardening
```

## 12. UI acceptance / test plan

### Functional

- Một người học tạo môn, upload tài liệu, đợi READY, hỏi AI, bấm citation mở đúng trang, làm quiz, xem tiến độ trong một phiên.
- Sau refresh/re-login: course, quiz results, learner plan không mất; unsent text recovery được quyết định rõ.
- Khi thay course: chat và citations gắn đúng course/document, không hiển thị nhầm data.
- Quota/error/retry/ingestion empty đều có trạng thái kết thúc; không vô hạn spinner.
- AI đề xuất ghi memory/thay plan cần approval và có audit trail.

### Responsive & A11y

- QA ở 360×800, 390×844, 768×1024, 1280×800, 1440×900; không horizontal overflow tại body.
- Không có CTA bị bottom nav hoặc keyboard che; sticky composer hoạt động iOS/Android.
- Bấm/chạm không nhầm (touch targets ≥44px ưu tiên), keyboard focus order hợp lý.
- Form errors, agent activity, upload status có accessible labels/live regions phù hợp.
- Reduced motion; color contrast kiểm tra công cụ tự động và thủ công.

### Reliability & security

- Chỉ hiển thị citation thực; citation không thuộc tài liệu của user không mở được.
- Không show secret, SQL connection string, raw reasoning hoặc provider credentials.
- Markdown được sanitize; HTML tải lên không thực thi script.
- E2E: first-use, resume, question+source, quiz correctness, quota failure, session isolation, logout/login account switch.

### Telemetry (opt-in/tuân thủ privacy)

`onboarding_completed`, `document_uploaded`, `document_ready`, `tutor_question_sent`, `citation_opened`, `quiz_completed`, `review_completed`, `recommended_task_accepted`, `task_abandoned`; đo task completion và errors, không log nội dung tài liệu/đề thi nhạy cảm mặc định.

### Quality targets (goals, not measured facts)

- Không critical UX blocker trên phone 360px.
- First study task tìm thấy và thực hiện được trong ≤3 click/tap chính sau khi có course/tài liệu READY.
- 100% citations trong UI có metadata nguồn thực và link/preview tương ứng hoặc trạng thái không còn khả dụng.
- Không có source giả, answer fallback A khi không parse được, hay incomplete long-running activity đứng mãi.
- Core learning funnel có E2E test và storybook/component states được kiểm chứng.

## 13. Design handoff checklist

- [ ] IA, sitemap, navigation desktop/mobile approved.
- [ ] 5 core screens high fidelity: Dashboard / Tutor / Materials / Quiz / Mobile.
- [ ] Additional screens: Course Path / Progress / Onboarding / Settings.
- [ ] Responsive variants + empty/loading/error/permission/quota states.
- [ ] Tokens + component specs + keyboard/focus + localizations vi-VN.
- [ ] API contracts versioned; frontend mocks align with real data.
- [ ] Citation component contract và agent activity event contract reviewed.
- [ ] Task acceptance user tests (3–5 learners) trước implementation freeze.
- [ ] QA mobile, regression smoke, privacy test and accessible navigation.

## 14. Sketch assets accompanying this plan

- `SELF_STUDY_SUPPORTER_UI_SKETCHES_OVERVIEW.png`: Dashboard, AI Tutor, Library, Quiz, Mobile.
- `SELF_STUDY_SUPPORTER_UI_DESIGN_BOARD.png`: Design goals, navigation, Dashboard, Agent Chat, Plan, Quiz, Library, Progress.
- `SELF_STUDY_SUPPORTER_MOBILE_WIREFRAMES.png`: Mobile home, tutor and quiz (precise readable wireframe).

**Cảnh báo:** Sketch là concept proposal, không phải frontend đã code hay screenshot từ production. Một số chữ nhỏ trong hình generative có thể mang tính minh họa; lấy nội dung và ràng buộc trong tài liệu này làm source of truth để implementation.

## 15. Architecture Decision Record — đề xuất chính thức

**ADR-UI-001: Next.js production UI + FastAPI backend + LangGraph events; Streamlit remains dev/eval UI.**

**Rationale:** Streamlit hiện phù hợp demo/prototype nhưng đang chứa ingestion + orchestration trong callback UI, làm khó responsive sâu, tiến trình nền, resume và quản lý state theo course. Web frontend tách biệt giúp xây UX học tập focus-mode, mobile-first, typed SSE và component tests. Không được thay đổi RAG algorithms chỉ vì thay UI.

**Risks:** tăng công sức fullstack; cần auth hardening, CORS/session, API contract, deployment riêng. **Mitigation:** migrate theo vertical slice với test và giữ baseline trên branch cũ; không viết lại AI Core; tùy nguồn lực có thể chạy Streamlit cải tiến làm bridge trong giai đoạn 1.

**Alternatives:** (a) Streamlit redesign: ship nhanh demo nội bộ, mobile/support workflow hạn chế; (b) React+Vite: gọn cho SPA thuần, vẫn phù hợp, ít backend SSR conventions hơn Next. Chọn sau khi xác nhận hosting strategy; đề xuất mặc định là Next.js + TS.

---

**Kết luận:** UI không chỉ “đẹp hơn” mà trở thành một lớp tương tác có hợp đồng dữ liệu rõ, phản ánh trạng thái học tập, kiểm soát Agent một cách đáng tin, và đảm bảo người dùng mobile tiếp tục học được ngay. Release v1.0.0 cần **end-to-end learning value** chứ không phải menu nhiều tính năng AI.
