# Kế hoạch chuyển đổi giao diện Self Study Supporter: Streamlit → Next.js + FastAPI

- **Trạng thái:** Proposed — chờ maintainer duyệt các ADR trước khi triển khai.
- **Ngày lập:** 2026-10-14.
- **Baseline:** nhánh **develop**, commit **88af014c4ce4736bf31841dc77eaf1c54ede98d9** (merge PR #14 — Refactor/legacy cleanup).
- **Phạm vi tài liệu:** kế hoạch kiến trúc, migration, delivery và acceptance; không thay đổi code nghiệp vụ trong commit này.
- **Mục tiêu cuối:** Next.js là giao diện chính; FastAPI là HTTP boundary; **backend/src/study_supporter** tiếp tục sở hữu core nghiệp vụ và AI/RAG. Streamlit được gỡ sau khi đạt đủ điều kiện cutover.

## 1. Tóm tắt quyết định

### Hướng được đề xuất

1. Xây giao diện mới bằng **Next.js + TypeScript**; ưu tiên thiết kế responsive, mobile-first và accessibility.
2. Xây **FastAPI** làm HTTP/API adapter; không đưa business logic, truy vấn SQL hay thao tác Chroma trực tiếp vào frontend.
3. Tái sử dụng application use cases, domain contracts, AI/RAG, persistence và provider adapters hiện có. Chỉ sửa core khi phát hiện một capability thật sự thiếu hoặc có lỗi được chứng minh bằng test.
4. Chuyển đổi theo **vertical slice**: mỗi giai đoạn hoàn tất một luồng có thể chạy end-to-end, không xây toàn bộ backend rồi mới bắt đầu UI.
5. Giữ Streamlit trong giai đoạn chuyển đổi để đối chiếu hành vi, nhưng không phát triển thêm feature mới trên Streamlit. Chỉ gỡ sau khi feature parity, regression, Docker và CI đạt gate.
6. Bảo toàn dữ liệu PostgreSQL, Chroma, model cache và các migration hiện tại. Không reset volume, đổi vector dimension, đổi collection naming hoặc thay schema chỉ để thuận tiện cho FE.
7. Chốt các quyết định chưa có trong code — nhất là session/auth, xử lý ingestion dài, API DTO và phạm vi feature parity — bằng ADR trước khi implementation tương ứng bắt đầu.

### Không làm

- Không viết lại RAG, embedding, retrieval, reranking, quiz generation hoặc orchestration chỉ vì chuyển UI.
- Không để Next.js truy cập trực tiếp PostgreSQL, Chroma, file storage hay provider keys.
- Không truyền user_id do client tự khai báo để quyết định quyền truy cập.
- Không coi tài liệu OpenAPI hiện tại là API đã chạy: docs/api/README.md xác nhận đây mới là proposal cho retrieval.
- Không xóa Streamlit hoặc đổi Docker volume ngay trong PR đầu tiên.
- Không thêm feature sản phẩm mới ngoài feature parity cần thiết để thay thế UI cũ.

## 2. Baseline repository đã xác minh

### Những gì đã có

- Core nằm tại **backend/src/study_supporter**, được chia thành domain, AI, application, infrastructure, orchestration và bootstrap.
- ApplicationFactory trong **study_supporter/bootstrap.py** quản lý tài nguyên process-scoped; **open_document(...)** tạo learning session theo user/document. Đây là composition path cần được API layer tái sử dụng.
- Application use cases hiện có gồm authentication, document ownership, ingestion, answer question, retrieval, quiz generation/submission, progress, notes và build learning path.
- Persistence gồm SQLAlchemy/PostgreSQL và Chroma. Bảng document hiện có trạng thái processing / ready / failed, số trang/chunks, hash file và concept graph JSON.
- UI hiện tại nằm tại **apps/streamlit_legacy**, gọi application services qua application_bridge.py.
- Có test unit, contract, import-boundary và PostgreSQL integration; workflow **.github/workflows/quality.yml** có các job offline, postgres và docker.
- Compose hiện tại dùng một service app, PostgreSQL và các volume có tên; Docker image đang khởi chạy Streamlit ở cổng 8501 và health check **/_stcore/health**.
- **backend/pyproject.toml** và **requirements/runtime.txt** còn khai báo Streamlit. FastAPI xuất hiện trong dependency lock hiện tại như dependency bắc cầu; không được dựa vào dependency bắc cầu đó làm API runtime contract.

### Những gì chưa có / chưa được xác nhận

- Chưa có FastAPI app runtime được công bố như API chính thức.
- Chưa có Next.js app trong repository.
- **docs/api/openapi.yaml** chỉ mô tả proposal retrieval, chưa phải contract đầy đủ cho auth, upload, chat, quiz, progress hay ingestion status.
- Chưa có quyết định cuối về cookie/session, CSRF, API versioning, timeout/retry và xử lý job ingestion dài.
- Lịch sử quiz trong Streamlit hiện lưu trong session state; không được ngầm cam kết nó đã persist qua đăng xuất/restart.
- Chưa có document-delete use case đã được xác nhận là an toàn cho cả SQL lẫn Chroma. Không tự thêm nút delete chỉ dựa trên UI mong muốn.
- Việc chạy đồng thời Streamlit và API trên cùng Chroma path cần được kiểm thử trước khi cho phép hai process cùng ghi vào dữ liệu đó.

## 3. Kiến trúc đích

    Browser
      └── Next.js + TypeScript
            ├── Pages / layouts / accessible UI components
            ├── Auth-aware API client; không giữ provider secrets
            └── Same-origin /api proxy
                  └── FastAPI
                        ├── Authentication + request scope
                        ├── DTO validation / HTTP error mapping
                        ├── Lifespan + resource lifecycle
                        └── ApplicationFactory / application use cases
                              ├── Domain contracts and policies
                              ├── AI / RAG / orchestration
                              └── Infrastructure adapters
                                    ├── PostgreSQL / SQLAlchemy
                                    ├── Chroma
                                    ├── Embedding model
                                    └── Ollama / cloud LLM providers

### Quy tắc ranh giới

- **Next.js** chịu trách nhiệm trình bày, điều hướng, form state, loading/error/empty states và gọi API.
- **FastAPI** chịu trách nhiệm HTTP contract, authentication, authorization context, request validation, status code, rate limit và mapping lỗi.
- **Application layer** chịu trách nhiệm use case và workflow.
- **Domain / AI core** không phụ thuộc FastAPI, Next.js hoặc Streamlit.
- **Infrastructure** giữ trách nhiệm về SQLAlchemy, Chroma, file parsing, embeddings và provider adapters.
- **Bootstrap/lifespan** tạo tài nguyên process-scoped một lần và đóng chúng khi process dừng. Không khởi tạo model, engine hoặc kết nối nặng khi import module.
- Account-bound session, tool hoặc conversation state phải được tạo theo authenticated user/document; không cache một learning session của người dùng trong biến global.
- API routes không được gọi sâu vào internal implementation nếu đã có application use case hoặc factory entrypoint phù hợp. Nếu thiếu entrypoint, bổ sung facade có test thay vì làm rò infrastructure lên HTTP layer.

### Runtime/deployment đích

Trong giai đoạn cuối, Compose dự kiến có:

- **web:** Next.js, publish cổng UI ra host; ưu tiên reverse proxy same-origin cho đường dẫn /api.
- **api:** FastAPI/Uvicorn, chỉ nhận traffic từ web/internal network trừ khi có quyết định expose API riêng.
- **db:** giữ PostgreSQL service và volume hiện tại.
- **migrate:** tiếp tục chạy Alembic trước khi API nhận traffic.
- **local-ai (optional):** giữ profile Ollama nếu người dùng chọn model local.
- **persistent data/cache:** tiếp tục giữ Chroma/app data và Hugging Face cache theo volume đã có.

Không đổi tên hoặc xóa volume hiện tại một cách máy móc. Trước khi đổi mount path hoặc chia Docker image, phải chứng minh API đọc được dữ liệu cũ bằng một restore/cutover rehearsal.

## 4. Phạm vi sản phẩm và feature parity

Đây là checklist kiểm kê và chuyển giao hành vi hiện có, không phải giấy phép mở rộng scope.

| Nhóm | Hành vi cần được kiểm kê và hỗ trợ trên UI mới | Điều kiện lưu ý |
|---|---|---|
| Tài khoản | Đăng ký, đăng nhập, đăng xuất, hiển thị trạng thái đăng nhập | User identity phải được suy ra từ session đã xác thực |
| Tài liệu | Upload PDF, validate file, phát hiện nội dung trùng, xem danh sách/mở tài liệu đã có | Tôn trọng ownership và status hiện tại; xác minh API cần trả metadata nào |
| Ingestion | Trạng thái processing/ready/failed, thông báo lỗi có thể hành động | Không giả lập progress phần trăm nếu backend không cung cấp tiến độ đáng tin |
| Trợ lý học tập | Gửi câu hỏi theo tài liệu đã chọn, hiển thị câu trả lời | Không gọi provider khi không có evidence/context phù hợp theo contract hiện có |
| Nguồn trích dẫn | Hiển thị evidence nguồn, tên tài liệu, trang nếu có | Citation phải đến từ evidence thật trả về; không tạo nguồn trang trí |
| Chọn model | Giữ hành vi Auto/Gemini/Ollama nếu config hiện tại hỗ trợ | Không trả API keys hoặc provider secrets về browser |
| Quiz | Tạo quiz theo tài liệu/chủ đề/số câu, chọn đáp án, nhận chấm điểm và giải thích | Giữ validate đúng 4 lựa chọn/1 đáp án đúng; không giả định quiz history đã persist |
| Concept graph / learning path | Hiển thị graph/path khi dữ liệu tồn tại; có trạng thái chưa tạo/thất bại | Không làm crash trang khi graph trống hoặc có chu trình |
| Notes / progress | Kiểm kê các use case hiện có và đưa lên UI nếu đang là hành vi người dùng được hỗ trợ | Giữ scope theo dữ liệu và contract thực tế; xác minh ownership/filter |
| Lỗi/provider quota | Thông báo lỗi dễ hiểu, retry hợp lý, lựa chọn local fallback nếu hiện có | Không hiển thị stack trace, credentials hoặc prompt nội bộ |
| Responsive/accessibility | Dùng được trên desktop và mobile, bàn phím, focus rõ, label và thông báo lỗi | Không chỉ kiểm thử screenshot desktop |

### Quyết định về feature parity

Trước khi bắt đầu frontend feature, AI Lead + System Dev phải tạo một **legacy behavior inventory** ngắn, liên kết mỗi hành vi với:
1. component Streamlit hiện tại;
2. application use case/facade hiện có;
3. API endpoint và DTO dự kiến;
4. test hiện tại hoặc test mới cần viết;
5. trạng thái: giữ nguyên, cải tiến nhỏ cần thiết, hoặc defer có ghi nhận.

Mọi mục defer phải được maintainer chấp thuận. Không gọi một luồng là “đã migrate” chỉ vì trang UI tồn tại; luồng phải chạy được từ request đến persistence/provider và quay lại UI.

## 5. Quyết định kiến trúc cần chốt bằng ADR

### ADR-01 — Frontend stack và cấu trúc

**Đề xuất:** Next.js App Router + TypeScript, package manager và lockfile duy nhất; lựa chọn UI/component library trong ADR thay vì thêm nhiều thư viện song song.

Cần chốt:
- phiên bản Node LTS và Next.js được pin;
- cấu trúc apps/web hoặc thư mục frontend thống nhất;
- lint, typecheck, unit test, build và cách sinh API types;
- quy ước server/client components và API client;
- thiết kế responsive, accessibility và ngôn ngữ giao diện.

**Gate:** không bắt đầu feature UI khi skeleton chưa có lint, typecheck, build và error boundary tối thiểu.

### ADR-02 — Authentication, session và CSRF

Core hiện có đăng ký/xác thực username-password và trả AppContext; nó chưa phải HTTP session implementation.

**Đề xuất mặc định cho self-host:** opaque server-side session cookie, cookie HttpOnly, Secure ở môi trường HTTPS, SameSite=Lax (hoặc nghiêm hơn nếu luồng không bị ảnh hưởng), thời hạn rõ ràng, session rotation khi đăng nhập và revoke khi logout. Nếu session lưu trong DB, chỉ lưu hash của token ngẫu nhiên; không lưu token thô. Dùng CSRF protection/Origin validation cho request thay đổi trạng thái. Cấu hình local HTTP phải có chế độ cookie an toàn phù hợp mà không làm giảm production defaults.

ADR phải quyết định:
- lưu session ở DB hay dùng một phương án khác;
- idle/absolute expiry và cách revoke;
- migration additive nếu cần bảng session;
- chống brute force/rate limit cho auth;
- xử lý registration trùng username;
- CSRF và same-origin proxy;
- cách kiểm thử logout, expiry, rotation và cookie flags.

**Không chấp nhận:** lưu session token dài hạn trong localStorage; tin user ID từ query/body/header do client tự chọn; chỉ bảo vệ trang ở Next.js nhưng không bảo vệ API.

### ADR-03 — Ingestion dài và progress

Use case ingestion hiện là synchronous và có callback progress; Compose chưa có worker queue riêng.

**Đề xuất cho migration MVP:** API tạo trạng thái document/job rõ ràng, giới hạn concurrency, chạy công việc nặng ngoài event loop và để UI polling status. Cách dispatch ban đầu phải được chọn có chủ đích (ví dụ bounded in-process worker cho local MVP); ghi rõ rằng job in-process không bảo đảm sống sót qua restart. Khi cần vận hành bền vững hoặc nhiều API replicas, bổ sung durable worker/queue bằng một ADR riêng.

ADR phải trả lời:
- API upload trả kết quả đồng bộ hay 202 Accepted;
- document ID/job ID và trạng thái có thể quan sát;
- cách xử lý request trùng theo hash;
- timeout, retry, cancel và stuck processing sau restart;
- giới hạn kích thước file, thời gian và số job đồng thời;
- progress stage nào thật sự có từ core; không biến stage thành phần trăm giả;
- cách ghi nhận lỗi và cleanup tệp tạm.

Không dùng FastAPI BackgroundTasks như thể đó là durable queue. Không để tác vụ model nặng chạy trực tiếp trên event loop async.

### ADR-04 — API contract/versioning

- Dùng prefix /api/v1 cho contract công khai đầu tiên.
- OpenAPI là source of truth; cập nhật contract trước hoặc cùng PR implementation.
- DTO tách khỏi ORM model và internal domain object.
- Error envelope thống nhất, ví dụ code/message/request_id; không trả exception stack.
- Mỗi route phải nêu authentication, ownership, status code, idempotency/retry behavior và giới hạn request.
- Sinh/kiểm tra TypeScript API types từ OpenAPI hoặc cơ chế tương đương; tránh tự duy trì hai schema lệch nhau.
- Breaking change phải tăng version hoặc được review theo compatibility policy.

### ADR-05 — Cutover và dữ liệu

- Quy định rõ Compose service, port, health endpoint, volumes và đường dẫn Chroma.
- Chạy regression bằng dữ liệu synthetic trước; sau đó diễn tập backup/restore trên bản sao volume.
- Không chạy hai process ghi đồng thời vào cùng Chroma persistence path trước khi xác minh multi-process safety.
- Nếu cần chạy song song để đối chiếu UI, dùng bản sao dữ liệu hoặc chế độ một writer duy nhất.
- Không drop cột/bảng, recreate database, đổi embedding model/dimension hoặc tái index tự động trong migration FE.
- Rollback phải là chuyển traffic về UI cũ với dữ liệu tương thích, không phải xóa dữ liệu mới.

## 6. API contract đề xuất để review

Danh sách dưới đây là **draft cho ADR-04**, không phải cam kết rằng các route đã tồn tại. AI Lead và System Dev phải map từng route sang use case/factory trước khi freeze.

| Khu vực | Endpoint dự kiến | Ghi chú contract |
|---|---|---|
| Health | GET /health/live | Chỉ xác nhận process còn sống |
| Health | GET /health/ready | Kiểm tra dependency cần thiết; không bắt buộc tải model embedding chỉ để trả health |
| Auth | POST /api/v1/auth/register | Validate username/password; không trả credential |
| Auth | POST /api/v1/auth/login | Tạo session/cookie theo ADR-02 |
| Auth | POST /api/v1/auth/logout | Revoke session và clear cookie |
| Auth | GET /api/v1/auth/me | Trả identity/profile tối thiểu của principal hiện tại |
| Documents | GET /api/v1/documents | Chỉ trả tài liệu thuộc user hiện tại |
| Documents | POST /api/v1/documents | Multipart PDF; trả document/job status theo ADR-03 |
| Documents | GET /api/v1/documents/{document_id} | Ownership check trước khi trả metadata/status |
| Chat | POST /api/v1/documents/{document_id}/chat | Câu hỏi và evidence/citations có cấu trúc; không tin document ID nếu chưa authorize |
| Quiz | POST /api/v1/documents/{document_id}/quizzes | Tạo quiz theo request schema được validate |
| Quiz | POST /api/v1/documents/{document_id}/quiz-attempts | Nộp đáp án, trả kết quả và ghi progress; idempotency cần được quyết định |
| Learning | GET/POST /api/v1/documents/{document_id}/learning-path | Đọc hoặc tạo graph/path tùy capability thực tế và thời gian xử lý |
| Progress | GET /api/v1/progress | Chỉ tổng hợp dữ liệu của principal |
| Notes | POST /api/v1/notes | Chỉ mở nếu semantics/ownership của notes đã được xác nhận |

Contract cho mỗi endpoint cần ghi:
- request/response schema, required/optional fields, size limits;
- success/error status và error code ổn định;
- auth required và ownership rule;
- retry/idempotency behavior;
- timeout và semantics với tác vụ dài;
- dữ liệu nhạy cảm không bao giờ được trả;
- test contract gồm happy path, invalid input, unauthenticated và cross-user.

### Error mapping tối thiểu

| Trường hợp | HTTP dự kiến | Quy tắc |
|---|---:|---|
| Chưa xác thực / session hết hạn | 401 | Không rò thông tin tài khoản |
| Đã xác thực nhưng không có quyền | 404 hoặc 403 theo ADR | Với document ID thuộc user khác, ưu tiên 404 để tránh enumeration |
| Request sai schema / file không hợp lệ | 422 | Thông báo có thể hành động |
| Rate limit / quota | 429 | Có thể kèm Retry-After khi phù hợp |
| Provider/model tạm unavailable | 503 | Không trả provider key hoặc stack trace |
| Lỗi bất ngờ | 500 | Có request ID; chi tiết chỉ ở server log |

Không biến mọi lỗi thành 200 kèm message; frontend phải dựa trên status/error code, không parse câu chữ để quyết định flow.

## 7. Kế hoạch triển khai theo phase và PR

Mỗi PR nên có một mục tiêu kiểm chứng được, thay đổi hẹp và có test. Không gộp migration UI, auth redesign, retrieval refactor và DB cleanup vào một PR.

### Phase 0 — Architecture decision + contract freeze

**PR:** docs/adr/nextjs-fastapi-migration-decisions

**Owner:** AI Lead + System Dev; AI Dev hỗ trợ mapping core.

**Công việc**
- Viết ADR-01 đến ADR-05, chốt stack, auth, ingestion, API versioning và cutover.
- Lập legacy behavior inventory và feature parity matrix.
- Hoàn thiện OpenAPI cho MVP: auth, documents/upload status, chat/citations; đánh dấu endpoint quiz/progress/notes là phase sau nếu chưa map được.
- Xác định DTO và error envelope; xác định endpoint ownership policy.
- Ghi rõ API contract nào là stable, field nào chưa chốt.
- Xác nhận CI hiện tại xanh trước khi mở runtime implementation.

**Acceptance**
- Không có route nào được đưa vào contract mà chưa có owner/use case hoặc quyết định bổ sung capability.
- Mọi thay đổi schema được ghi trong ADR; nếu chưa cần, giữ nguyên schema.
- Có danh sách feature parity, test và điều kiện remove Streamlit.
- Maintainer approve các ADR auth, ingestion và data cutover.

### Phase 1 — FastAPI runtime foundation

**PR:** feature/fastapi-runtime-auth

**Owner:** System Dev (primary), AI Dev (application adapter), AI Lead (review).

**Công việc**
- Thêm FastAPI/Uvicorn như dependency trực tiếp được pin; không dựa vào dependency bắc cầu.
- Tạo API package/app factory tách biệt với Streamlit; cấu hình Settings từ environment rõ ràng.
- Dùng FastAPI lifespan để tạo ApplicationFactory một lần, verify schema theo quy trình migration hiện tại và close resources khi shutdown.
- Thêm /health/live, /health/ready, request ID, logging có cấu trúc, exception mapping và validation.
- Xây auth adapter cho register/login/me/logout dựa trên ApplicationFactory.authentication; implement session theo ADR-02.
- Tạo authenticated principal/context ở dependency/middleware; không nhận user_id do client quyết định.
- Tách DTO HTTP khỏi ORM; không trả password hash, session token, provider secret hoặc internal exception.
- Bổ sung tests bằng FastAPI TestClient/HTTPX với DB test fixture; không gọi cloud provider thật.

**Acceptance**
- API khởi động và shutdown sạch; không khởi tạo model nặng chỉ bằng import.
- Auth tests gồm register, duplicate username, invalid credentials, logout, expired/revoked session và cookie flags.
- Test route không cho client giả mạo identity.
- Readiness phản ánh dependency thật nhưng không kích hoạt tải model.
- Existing unit/contract/Postgres tests không bị regression.
- Chưa cần gỡ Streamlit và chưa đổi vector storage.

### Phase 2 — Next.js foundation + auth vertical slice

**PR:** feature/web-app-shell-auth

**Owner:** System Dev (API integration/build), AI Dev (UI flows), AI Lead (UX/product acceptance).

**Công việc**
- Tạo frontend app, TypeScript strict, lockfile, lint, typecheck, unit test và production build.
- Thiết lập layout, design tokens, responsive navigation, loading/error/empty states và accessible form primitives.
- Tạo API client tập trung, xử lý 401/422/429/503 theo error envelope; không duplicate URL/config rải rác.
- Implement register/login/logout/me; route guard chỉ là UX, API vẫn phải tự authorize.
- Chốt same-origin proxy cho /api; tránh CORS wildcard.
- Bổ sung test form validation, pending state, duplicate submission và session expiry.
- Tạo trang authenticated shell và trạng thái chưa có tài liệu.

**Acceptance**
- Người dùng đăng ký, đăng nhập, reload trang, tiếp tục session hợp lệ và đăng xuất được.
- API không cho truy cập protected route sau logout/expiry.
- Không có token/provider secret trong localStorage, source map hay client bundle.
- UI dùng được trên mobile và desktop; keyboard/focus/labels có test cơ bản.
- Frontend build chạy độc lập khỏi Streamlit.

### Phase 3 — Document library + upload/ingestion

**PR:** feature/web-document-ingestion

**Owner:** AI Dev (use-case integration/progress mapping), System Dev (API/job execution), AI Lead (file UX and acceptance).

**Công việc**
- Implement document list/latest/open/status endpoints theo ownership contract.
- Implement PDF upload và validation: MIME/extension/content, size limit, duplicate hash và lỗi dễ hiểu.
- Map status hiện có processing/ready/failed sang UI; hiển thị stage thật nếu callback có dữ liệu phù hợp.
- Chọn cơ chế xử lý tác vụ theo ADR-03; giới hạn concurrency, timeout và tài nguyên.
- Tạo UI cho upload pending, progress/status polling, retry khi an toàn, failed state và mở lại tài liệu đã có.
- Xử lý stuck processing sau restart theo chính sách đã chốt.
- Viết integration tests cho PDF text, blank/corrupt PDF, duplicate, embedding/provider failure và upload cleanup.

**Acceptance**
- Upload hợp lệ tạo document và cuối cùng về ready hoặc failed; không bị trạng thái giả.
- User A không thể xem status hoặc nội dung document của user B.
- Retry upload cùng nội dung không tạo duplicate sai semantics.
- Lỗi parser/embedding không làm mất record hoặc để tệp tạm rác không kiểm soát.
- UI không gửi nhiều upload/job do double-click hoặc rerender.
- Không thay đổi Chroma collection naming/vector dimension nếu không có ADR riêng.

### Phase 4 — Chat + evidence/citations

**PR:** feature/web-chat-citations

**Owner:** AI Lead (answer grounding/quality), AI Dev (session/use-case adapter), System Dev (API/streaming/security).

**Công việc**
- Implement chat API dựa trên learning session/use case hiện có; tạo session theo authenticated user và document được authorize.
- Chuẩn hóa response: answer, request/conversation metadata nếu cần, citations/evidence gồm document/chunk/source/page/score khi có.
- Quyết định response sync hay streaming. Nếu streaming, chốt SSE event schema, heartbeat, disconnect cleanup và error event trước khi FE tích hợp.
- Tạo chat UI: empty state, pending indicator, retry phù hợp, lỗi quota/provider và citation list có thể mở rộng/thu gọn.
- Giữ quy tắc không gọi provider khi retrieval không có context hợp lệ theo contract đã test.
- Không đưa prompt nội bộ hoặc raw tool trace ra UI.

**Acceptance**
- Upload → ready → hỏi → retrieval → answer → citation chạy end-to-end với fixture deterministic.
- Citation UI chỉ hiển thị evidence backend trả về.
- Request không thể trỏ sang document của user khác.
- Không có câu trả lời được tạo bằng cách giả lập evidence khi retrieval rỗng.
- Disconnect/timeout không để request/task/connection rò rỉ.
- Có test provider failure, quota, empty retrieval và invalid document.

### Phase 5 — Quiz, progress, notes và learning path

**PR đề xuất:**
- feature/web-quiz-progress
- feature/web-learning-path-notes

**Owner:** AI Lead (learning behavior/quality), AI Dev (use cases, DTO), System Dev (API/UX integration).

**Công việc**
- Tạo quiz theo document/topic/count và trả schema typed, validate 4 options và một correct answer.
- Submit đáp án qua API, ghi attempt/progress bằng use case hiện có, chống submit lặp theo policy được chốt.
- Hiển thị feedback và explanation sau khi nộp; không gửi correct answer về client trước thời điểm phù hợp.
- Hiển thị progress summary; kiểm tra các query đều lọc theo principal.
- Hiển thị concept graph/learning path; có fallback khi chưa có graph, graph rỗng hoặc graph có cycle.
- Tích hợp notes chỉ sau khi xác nhận semantics lưu trữ và isolation; không đổi note storage một cách ngầm định.
- Quyết định rõ quiz history là session-only hay persistence mới. Nếu cần persistence lâu dài, tạo feature/schema migration riêng và test; không giả vờ parity khi dữ liệu chưa được lưu.

**Acceptance**
- Quiz generation failure trả lỗi rõ ràng và không làm hỏng phiên học.
- Submit quiz kiểm tra ownership, selected index và câu hỏi/đáp án hợp lệ.
- Progress được ghi đúng user/document; test isolation giữa hai tài khoản.
- Graph/path render không crash khi thiếu dữ liệu.
- Feature nào chưa có backend support được ghi defer, không tạo UI nút giả.

### Phase 6 — Compose, CI, production hardening và cutover

**PR:** chore/remove-streamlit

**Owner:** System Dev/DevOps (primary), AI Dev (regression), AI Lead (final acceptance).

**Điều kiện bắt buộc trước khi mở PR**
- Phase 2–5 đã merge và regression matrix được tick đầy đủ.
- API + web chạy end-to-end trên bản sao dữ liệu.
- Backup/restore rehearsal hoàn tất.
- Có kế hoạch rollback đã thử nghiệm.
- Không còn feature nào cần Streamlit làm đường truy cập duy nhất.

**Công việc**
- Thêm Dockerfile production cho API và web; pin dependencies và build reproducible.
- Chuyển Compose sang web/api/db/migrate, giữ local-ai profile nếu còn cần.
- Healthcheck chuyển sang /health/live hoặc /health/ready theo mục đích; không giữ healthcheck phụ thuộc Streamlit.
- Cập nhật port, internal network, env examples, secrets handling, resource limits và shutdown behavior.
- Kiểm tra volume mapping; API phải dùng đúng Chroma/app-data/HF cache cũ.
- Chạy CI: Python unit/contract, PostgreSQL migration/integration, frontend lint/typecheck/unit/build, API tests và Compose smoke.
- Chỉ sau khi CI không phụ thuộc Streamlit mới xóa apps/streamlit_legacy, .streamlit, Streamlit-specific tests/config và Streamlit khỏi runtime dependency lock.
- Cập nhật README, Docker docs, local dev docs, troubleshooting, architecture diagram và API docs.
- Tìm và loại bỏ command redirect/legacy import/documentation nào chỉ còn phục vụ Streamlit, nhưng không xóa compatibility path còn được người dùng sử dụng mà chưa có thông báo.

**Acceptance**
- Cài đặt mới bằng Compose chạy được web + API + PostgreSQL; healthcheck đúng.
- Backup dữ liệu cũ, khởi chạy phiên bản mới và đọc được documents/quiz attempts/progress/concept graph cũ theo khả năng hiện tại.
- Không có migration/drop volume/Chroma reset ngoài ý muốn.
- CI không cài hoặc chạy Streamlit để kiểm chứng sản phẩm chính.
- README chỉ hướng dẫn UI mới; không còn chỉ dẫn nhầm cổng 8501.
- Rollback đã được thử trên môi trường test bằng cách chuyển về image/compose cũ và dữ liệu vẫn đọc được.
- PR được review như một cutover có rủi ro, không merge chỉ vì UI trông hoàn chỉnh.

## 8. Phân công vai trò và trách nhiệm

| Vai trò | Trách nhiệm chính | Phải review |
|---|---|---|
| AI Lead | Chốt hành vi AI/RAG, evidence/citation contract, chất lượng quiz, feature parity và acceptance người học | ADR-03/04, chat/citations, quiz, learning path, regression |
| AI Dev | Map use cases hiện có sang API, xây adapter/DTO cần thiết, viết integration fixtures và giữ core độc lập framework | API-to-use-case mapping, tests, mọi thay đổi core |
| System Dev | Kiến trúc API/frontend boundary, auth/session, API contract, lifecycle, Docker, DB migrations, security và deployment | ADR-01/02/04/05, Compose, CI, auth, ownership |
| QA/DevOps | Thiết kế test matrix, synthetic fixtures, CI, container smoke, backup/restore và rollback rehearsal | Mọi gate trước khi chuyển phase/cutover |
| Maintainer/Product owner | Chấp thuận scope, trade-off, defer, schema change và cutover | ADR, scope changes, Phase 6 |

### Quy tắc phối hợp

- AI Lead không thay System Dev tự quyết session/security; System Dev không tự thay semantics RAG/citation để tiện triển khai UI.
- AI Dev phải chứng minh một use case hiện có đáp ứng nhu cầu trước khi đề xuất viết lại core.
- Mỗi PR có một owner chịu trách nhiệm và ít nhất một reviewer phù hợp với ranh giới bị thay đổi.
- Thay đổi core, DB schema, Chroma layout hoặc API contract đều phải nêu lý do và regression evidence trong PR description.
- Không mở phase kế tiếp nếu acceptance gate phase trước còn đỏ, trừ khi maintainer chấp thuận exception được ghi lại.

## 9. Kiểm thử và CI

### Test pyramid

1. **Domain/unit:** giữ nguyên test hiện có cho chunking, RRF, quiz validation, empty retrieval, citations, provider errors, document ownership, notes isolation và session reset.
2. **Application contract:** test DTO/port/use-case behavior, không phụ thuộc FastAPI hoặc Streamlit.
3. **API contract:** status/schema/error envelope/auth/ownership qua FastAPI TestClient/HTTPX.
4. **Integration:** PostgreSQL migrations/repositories; Chroma integration với thư mục tạm và embedding fake; không cần cloud credentials.
5. **Frontend:** unit test form/state/error handling; typecheck; lint; production build.
6. **E2E/Compose:** auth → upload synthetic PDF → processing → chat → citations → quiz submit/progress; chạy local model/provider thật ở job opt-in, không làm CI offline phụ thuộc network.
7. **Operations:** backup/restore, restart khi processing, session expiry, readiness/liveness, rollback.

### Regression matrix bắt buộc

| Tình huống | Kết quả mong đợi |
|---|---|
| User chưa login gọi document/chat API | 401 |
| User A đọc document của user B | Không tiết lộ document; 404/403 theo ADR |
| PDF sai MIME/nội dung hoặc vượt giới hạn | 422 và không để trạng thái/file rác |
| PDF hợp lệ nhưng parser/embedding lỗi | Document failed, lỗi hiển thị an toàn, có thể retry theo policy |
| Upload cùng nội dung nhiều lần | Dedupe theo contract; không tạo collection/chunk trùng ngoài ý muốn |
| Retrieval không có evidence | Không gọi LLM để bịa nguồn; UI cho biết chưa có ngữ cảnh phù hợp |
| Provider quota/unavailable | 429/503 mapping ổn định, không lộ secret |
| Quiz có option thiếu/trùng/đáp án sai | Validation fail closed |
| Submit quiz hai lần | Hành vi idempotency rõ; progress không tăng đôi ngoài policy |
| Logout/expire session | Protected API bị từ chối |
| Restart API khi ingestion đang chạy | Trạng thái được phục hồi hoặc đánh dấu failed theo ADR-03 |
| Graph rỗng/có cycle | UI có fallback, không crash |
| Backup data cũ rồi deploy web/API | Dữ liệu cũ đọc được; không tự reset Chroma/DB |
| Frontend/API dừng hoặc dependency không sẵn sàng | Health/readiness và error UI phản ánh đúng tình trạng |

### CI thay đổi theo lộ trình

- Giữ job offline và PostgreSQL hiện tại.
- Thêm frontend lint/typecheck/unit/build khi có apps/web.
- Thêm API tests và contract/OpenAPI consistency check khi có FastAPI.
- Docker job smoke endpoint API/web, migration, và test không cần model.
- Giữ test Streamlit trong thời gian dual-run nếu còn hữu ích; loại bỏ sau cutover, không xóa sớm để làm CI xanh giả.
- Không yêu cầu credentials cloud hoặc download model lớn trong CI mặc định.
- Mọi dependency API phải là dependency trực tiếp được pin; cập nhật lock theo một quy trình duy nhất.

## 10. Bảo mật, quyền riêng tư và vận hành

### Security gates

- Principal lấy từ session đã xác thực; mọi truy vấn document/progress/notes đều scope theo principal.
- Không có user_id tự do trong request body để thay thế authentication.
- Không expose provider API keys, password hash, session token, prompt nội bộ hoặc exception stack.
- Cookie/session theo ADR-02; CSRF/Origin validation và rate limit cho auth/write endpoints.
- Upload chỉ chấp nhận PDF đã validate; giới hạn size, xử lý tên file an toàn, cleanup file tạm.
- Không log password, cookie, Authorization header, raw document content hoặc provider secret.
- CORS chỉ bật origin được cấu hình nếu thực sự cần cross-origin; ưu tiên same-origin reverse proxy.
- DB migration chạy bằng Alembic; không dùng import-time create_all() để tự thay đổi schema.
- API và frontend container chạy non-root khi khả thi; DB không publish ra public network; secret chỉ cấp cho service cần dùng.
- Health endpoint không leak config, model paths, credentials hoặc nội dung dữ liệu.

### Observability

- Mỗi request có request/correlation ID.
- Log method, route template, status, duration và error code; tránh log query/body nhạy cảm.
- Ghi metric cơ bản cho upload duration/failure, provider failure/quota, chat latency và API 5xx.
- Error UI hiển thị hành động tiếp theo; chi tiết debug ở server logs.
- Readiness không tải embedding model hoặc gọi cloud provider ở mỗi healthcheck.
- Timeout và concurrency limits phải tính đến embedding model BGE-M3, provider latency và giới hạn RAM/CPU hiện tại của Compose.

## 11. Dữ liệu, migration và rollback

### Nguyên tắc bảo toàn

- Không chạy docker compose down -v trong quá trình migration.
- Không đổi tên volume hoặc mount Chroma sang thư mục mới nếu chưa có copy/restore verification.
- Không đổi embedding model, vector dimension, collection naming hoặc chunk IDs chỉ để tối ưu API.
- DB schema change phải có Alembic migration và test upgrade từ baseline; ưu tiên additive change.
- Nếu cần bảng session, thêm migration riêng, index/expiry policy và test revoke; không sửa password storage hiện có ngoài phạm vi ADR.
- Document deletion nếu được thêm phải có ownership check và cleanup strategy cho SQL + Chroma; chưa có transaction phân tán thì cần quy tắc recovery rõ.
- Dùng synthetic PDFs và fake embeddings cho test; không đưa tài liệu cá nhân, credential hoặc dump production vào repository/CI.

### Cutover checklist

- [ ] CI xanh trên commit được cutover.
- [ ] Backup PostgreSQL và Chroma/app data; xác minh backup không nằm trong Git.
- [ ] Restore thử trên môi trường test.
- [ ] Chạy Alembic upgrade/check và kiểm tra dữ liệu cũ.
- [ ] Kiểm tra API đọc được document metadata, chunks, graph và progress cũ.
- [ ] Chạy smoke auth → upload → chat/citations → quiz/progress.
- [ ] Kiểm tra web/API health, logs và restart.
- [ ] Có image/tag và Compose cũ để rollback.
- [ ] Xác nhận không có hai writer đồng thời trên cùng Chroma path.
- [ ] Sau khoảng thời gian ổn định mới gỡ legacy service/code/dependencies.

### Rollback

1. Dừng nhận traffic vào web/API mới nếu có lỗi dữ liệu hoặc auth.
2. Khởi động lại image/Compose Streamlit đã giữ, trỏ tới dữ liệu tương thích.
3. Không xóa hoặc recreate volume trong rollback.
4. Nếu API mới đã chạy migration additive, xác minh UI cũ tương thích với schema mới; không tự động downgrade/drop dữ liệu.
5. Thu thập request ID/logs và tạo issue/PR sửa lỗi; không chữa cháy bằng cách đổi vector dimension hay xóa Chroma.
6. Chỉ thử cutover lại khi regression và restore rehearsal đã pass.

## 12. Definition of Done cho toàn bộ migration

Migration chỉ được coi là hoàn tất khi tất cả điều kiện sau đạt:

- [ ] Next.js là giao diện chính và đáp ứng feature parity đã được duyệt.
- [ ] FastAPI có OpenAPI contract đầy đủ, versioned, có auth và ownership tests.
- [ ] Core/application tests chạy độc lập khỏi UI framework.
- [ ] Auth/session/CSRF/logout/expiry đã được test; API không tin client-supplied user ID.
- [ ] Upload/ingestion, chat/citations, quiz, progress và các feature được giữ lại chạy end-to-end.
- [ ] UI hiển thị loading, empty, success và error states; dùng được trên mobile/desktop.
- [ ] PostgreSQL/Chroma/model cache và dữ liệu cũ được giữ; backup/restore đã diễn tập.
- [ ] Docker Compose chạy web/api/db/migrate; healthcheck không phụ thuộc Streamlit.
- [ ] CI chạy offline, PostgreSQL, frontend và Docker smoke không cần Streamlit.
- [ ] Streamlit code/config/dependencies/tests đã được loại bỏ sau cutover; không còn docs hướng dẫn cổng 8501.
- [ ] README, architecture docs, API docs, env examples và troubleshooting được cập nhật.
- [ ] Có rollback path đã kiểm thử và maintainer xác nhận.

## 13. Rủi ro chính và cách giảm thiểu

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Viết lại core cùng lúc với đổi UI | Regression lớn, khó xác định nguyên nhân | Tái sử dụng use case; test trước; core changes phải có ADR/test riêng |
| Auth chỉ được bảo vệ ở frontend | IDOR hoặc API bị gọi trực tiếp | Auth dependency + ownership test trên mọi endpoint |
| Ingestion đồng bộ chặn API | Timeout, UI tưởng treo, cạn worker | ADR-03, bounded concurrency, status polling, timeout và restart recovery |
| Dựa vào dependency bắc cầu | Build thay đổi bất ngờ, API không khởi động | Pin FastAPI/Uvicorn trực tiếp và lock reproducible |
| Hai process cùng ghi Chroma | Lock, dữ liệu lỗi hoặc behavior không xác định | Không dual-write cùng path trước khi kiểm thử; dùng data copy khi đối chiếu |
| Gỡ Streamlit quá sớm | Feature chưa chuyển xong, không có đường rollback | Phase 6 chỉ mở khi parity matrix và rehearsal pass |
| Quiz history bị mất sau migration | Người dùng kỳ vọng persistence không có thật | Nêu rõ semantics hiện tại; quyết định persistence riêng |
| Healthcheck chỉ báo process sống | Container “healthy” nhưng app không dùng được | Tách liveness/readiness; functional smoke riêng |
| Thêm UI cho capability chưa có | Nút lỗi/giả, tăng scope | Route-to-use-case map; defer có phê duyệt |
| Schema migration phá dữ liệu cũ | Mất document/progress | Additive migration, backup/restore rehearsal, không reset volume |

## 14. Thứ tự làm việc và quy tắc merge

Thứ tự dependency khuyến nghị:

1. Phase 0: ADR + feature inventory + API contract.
2. Phase 1: FastAPI runtime + auth/session.
3. Phase 2: Next.js shell + auth vertical slice.
4. Phase 3: document library + upload/ingestion.
5. Phase 4: chat + citations.
6. Phase 5: quiz/progress/learning path/notes.
7. Phase 6: Compose/CI cutover + remove Streamlit.

Có thể phát triển UI skeleton song song với Phase 1 khi contract auth đã được duyệt, nhưng không nên để frontend tự bịa schema rồi buộc API chạy theo schema chưa review.

### Quy tắc PR

- PR nhỏ, một mục tiêu; cập nhật checklist phase và test evidence trong description.
- Không gộp rename hàng loạt với thay behavior.
- Không merge khi CI đỏ hoặc contract/API types lệch nhau.
- Không thay đổi database/vector schema trong PR FE nếu không được ghi rõ.
- Mỗi PR phải nêu: scope, non-goals, API changes, security impact, data impact, tests run, rollback note.
- PR Phase 6 cần reviewer độc lập và cutover checklist đã hoàn tất.

### Ước lượng tương đối

Đây là migration có backend API, session security, frontend, integration và deployment; không chỉ là viết lại CSS. Ước lượng sơ bộ theo effort, cần điều chỉnh sau Phase 0:

- Phase 0: S — 1–2 ngày.
- Phase 1: M — 2–4 ngày.
- Phase 2: M — 2–4 ngày.
- Phase 3: M/L — 3–5 ngày.
- Phase 4: M/L — 3–5 ngày.
- Phase 5: L — 4–7 ngày.
- Phase 6: M — 2–4 ngày.

Tổng sơ bộ khoảng 17–31 engineer-days, chưa tính thời gian xử lý blocker ngoài dự kiến hoặc thay đổi scope. Đây là estimate để lập kế hoạch, không phải cam kết deadline.

## 15. Hành động tiếp theo

1. Review tài liệu này như migration proposal; không bắt đầu xóa Streamlit.
2. Duyệt ADR-02 (auth/session), ADR-03 (ingestion) và ADR-05 (data cutover) trước implementation.
3. Hoàn thiện feature parity inventory từ **apps/streamlit_legacy** và map sang **ApplicationFactory**/use cases.
4. Freeze API contract MVP trong **docs/api/openapi.yaml**; thêm auth, documents, chat và citations trước khi frontend tích hợp.
5. Tạo các feature branches riêng từ develop cho từng phase/PR. Nhánh tài liệu hiện tại không phải nhánh để tích hợp toàn bộ code.
6. Bắt đầu Phase 1 chỉ khi ADR và contract được maintainer chấp thuận.

**Quyết định cần maintainer xác nhận:** chấp thuận hướng Next.js + TypeScript / FastAPI, giữ core framework-independent, chuyển theo vertical slices, và chỉ remove Streamlit tại Phase 6 sau khi feature parity + data/rollback gates đạt.
