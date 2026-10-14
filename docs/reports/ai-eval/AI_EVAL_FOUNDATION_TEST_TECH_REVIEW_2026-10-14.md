# SELF STUDY SUPPORTER — TEST LEAD × TECH LEAD FIX REPORT

> **Tài liệu:** Defect review, technical improvement guide & verification checklist
> **Ngày review:** 14/10/2026
> **Repository:** [ManhT005/self-study_supporter](https://github.com/ManhT005/self-study_supporter)
> **Nhánh được review:** [`feature/ai-eval-foundation`](https://github.com/ManhT005/self-study_supporter/tree/feature/ai-eval-foundation)
> **Commit cố định:** [`679665b7d14c0d005d8a63724c649ca5957ddd4f`](https://github.com/ManhT005/self-study_supporter/commit/679665b7d14c0d005d8a63724c649ca5957ddd4f)
> **Base:** `develop` tại `4302d971c31e1944b3280b20d3f1fc9f83135ea4`
> **Reviewer:** Test Lead (static code review, CI evidence) — **bản hướng dẫn phối hợp kỹ thuật đề xuất**; chưa có xác nhận/phê duyệt độc lập từ Tech Lead.
> **Đích lưu trong repo (đề xuất):** `docs/reports/ai-eval/AI_EVAL_FOUNDATION_TEST_TECH_REVIEW_2026-10-14.md`

## 1. Quyết định review

**Kết luận: CONDITIONAL PASS cho engineering foundation; NOT ACCEPTED cho Phase 1 quality-benchmark gate.**

- **Đạt:** cấu trúc `AgentPort`/`AgentResult` độc lập framework; request-local evidence recorder; bảo toàn HTTP DTO; có versioned synthetic fixtures, manifests, structural metrics, test concurrency, scope checks và CI.
- **Chưa đạt:** một số metric có tên/ý nghĩa chưa tương thích chuẩn đánh giá retrieval; test privacy mới chứng minh synthetic precheck; coverage multi-search/tool selection chưa đủ để công bố benchmark đáng tin; chưa có báo cáo benchmark real-model ≥100 cases/frozen holdout/human review.
- **Khuyến nghị:** làm **một PR sửa metric + coverage trước**, không refactor lớn, không thay model, retriever, SQL/Chroma schema, prompt ReAct hoặc frontend trong cùng PR.

### 1.1 Evidence đã đối chiếu

| Bằng chứng | Kết quả / giới hạn |
|---|---|
| [`develop...feature/ai-eval-foundation`](https://github.com/ManhT005/self-study_supporter/compare/develop...feature/ai-eval-foundation) | Ahead 2 commits, 48 files changed tại thời điểm review |
| [GitHub Actions run #38546731224](https://github.com/ManhT005/self-study_supporter/actions/runs/38546731224) | `success`: **6/6 jobs** (`offline`, `api`, `postgres`, `web`, `workspace-docker`, `docker`) |
| [Local verification report](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/docs/reports/ai-eval/2026-10-14-foundation.md) | Tác giả báo cáo 153 Python/API tests qua local verification; synthetic CLI 90 records / 3 repetitions |
| [`evaluation/datasets/v1/smoke.jsonl`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/datasets/v1/smoke.jsonl) | **15 unique synthetic development cases**, không phải 90 câu hỏi và không phải real-provider benchmark |
| Phạm vi review | Đọc code, tài liệu và trạng thái CI từ GitHub; **chưa chạy độc lập các bài test/model trên máy Test Lead**; kết quả runtime nêu trên là bằng chứng CI hoặc báo cáo của repository |

**Phân biệt:** `Confirmed (static)` = logic code có thể chứng minh trực tiếp; `Coverage gap` = chưa có bài test cần thiết, **không đồng nghĩa đã có lỗ hổng runtime**; `Measurement limitation` = số đo có thể hợp lệ cho mục đích hẹp nhưng chưa đủ cho quality gate.

## 2. Defect & improvement register

| ID | Ưu tiên | Loại | Vấn đề / ảnh hưởng | Người dẫn dắt | Merge gate |
|---|---|---|---|---|---|
| **QA-01** | **P1** | Confirmed (static) | `recall_at_k` thực chất là **Hit Rate@k**; multi-hop bị đánh giá quá cao khi chỉ lấy được một phần bằng chứng | AI/Tech | **Block** |
| **QA-02** | **P1** | Coverage gap | Test `AUTH_SCOPE` mới chứng minh synthetic ownership precheck; cần qua production access adapter/API và bảo đảm không side effect | Backend + QA | **Block** |
| **QA-03** | **P1** | Confirmed (static) | `all([]) == True` làm `tool_selection_allowed=1` dù Agent không gọi tool | AI/Tech | **Block** |
| **QA-04** | **P1** | Measurement limitation | Đánh giá multi-search chỉ dùng `retrieval_calls[0]`, không phản ánh retry/search bổ sung | AI/Tech | **Block** |
| **QA-05** | **P1** | Coverage gap | CI chạy synthetic smoke nhưng chưa có golden metric thresholds/semantic benchmark gate được version hóa | QA + AI | **Block** đối với baseline signoff; không yêu cầu live model trong CI |
| **QA-06** | **P2** | Reporting issue | Expected `AUTH_SCOPE` denials vẫn được gộp vào `n_failed`, dễ gây hiểu nhầm độ ổn định | QA/AI | Nên sửa trong cùng PR nếu nhỏ |
| **QA-07** | **P2** | Coverage gap | Live paired runner nhận callback nhưng không tự xác minh isolation giữa lần lặp, cache/history/tool side effects | AI + Backend | Trước **real-model benchmark** |
| **QA-08** | **P2** | Semantic correctness | Evidence union của tất cả search được trả ra như citations dù chưa chứng minh từng đoạn hỗ trợ final answer | AI + Product | Trước claim-level citation quality gate |
| **QA-09** | **P2** | Benchmark readiness | Smoke thiếu `quiz`, `personalized`, prompt-injection; chưa có frozen validation/holdout và độc lập annotation | Test Lead + AI | Trước **Phase 1 acceptance** |

**P1:** bắt buộc xử lý trước khi dùng các số đo để quyết định công nghệ/accept baseline chính thức; **P2:** có thể tách PR nhưng phải đóng trước gate liên quan. Không coi tất cả P1 là lỗi chức năng người dùng đã xảy ra.

---

## 3. Hướng dẫn sửa chi tiết (Tech Lead implementation + Test Lead acceptance)

### QA-01 — Sửa sai tên/định nghĩa Recall@k [P1]

**Evidence:** [`evaluation/scoring.py#L17-L36`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/scoring.py#L17-L36)

Code hiện tại:

```python
first = next((i + 1 for i, gain in enumerate(gains) if gain), None)
scores.update(recall_at_k=float(first is not None), mrr_at_k=1 / first if first else 0.0)
```

**Vấn đề:** hit bất kỳ một relevant chunk trả về 1, trong khi Recall@k thông dụng đo `|retrieved_top_k ∩ relevant| / |relevant|`. Với gold `{A, B}` và kết quả `[A, X, Y]`, actual Recall@3 phải là `0.5` (code hiện tại báo `1.0`). Đây là xung đột với tên metric; roadmap hiện tại cố định định nghĩa custom, vì vậy sửa **code, tên bảng/README và tài liệu**, không sửa một phía.

**Tech implementation:**

```python
ranked_unique = list(dict.fromkeys(ranked[:top_k]))
gold = set(case.relevant_chunk_ids)
found = len(gold.intersection(ranked_unique))
hit_rate_at_k = float(found > 0)
recall_at_k = found / len(gold)  # Chỉ tính trên case có gold không rỗng
```

- Giữ `mrr_at_k` theo vị trí relevant đầu tiên, `ndcg_at_k` với duplicate suppression và ideal DCG đúng như logic đã có.
- Với dataset cũ, **không đổi nghĩa âm thầm**: xuất `hit_rate_at_k` mới, sửa `recall_at_k`, nâng `metric_schema_version` hoặc ghi migration note để các báo cáo cũ không bị so sánh nhầm.
- Nếu chấm trên `retrieval_calls`, phải xác định **which call** nhất quán theo QA-04.

**Test Lead cases:**

| Case | Gold | Retrieved@3 | Expected |
|---|---|---|---|
| TC-EVAL-01a | `{A, B}` | `[A, X, Y]` | `hit=1`, `recall=0.5` |
| TC-EVAL-01b | `{A, B}` | `[A, B, B]` | `hit=1`, `recall=1.0` (không đếm B lặp) |
| TC-EVAL-01c | `{A, B}` | `[X, Y, Z]` | `hit=0`, `recall=0`, `MRR=0` |
| TC-EVAL-01d | `{A}` | `[X, A, Y]` | `MRR=0.5` |
| TC-EVAL-01e | Không có gold (`unanswerable`) | Bất kỳ | Recall **N/A**, không tự gán 1 |

**Done:** assertions xác nhận semantics mới; docs/summary/experiment plots đồng bộ; report cũ có thể phân biệt schema version.

### QA-02 — Production-path authorization & no-side-effect tests [P1]

**Evidence:** [`evaluation/synthetic.py#L83-L94`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/synthetic.py#L83-L94) kiểm tra owner **trước** khi gọi agent; [`evaluation/errors.py`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/errors.py) ánh xạ `EvidenceNotFound` → `NO_EVIDENCE`.

**Tech implementation:**

1. Tạo test integration với fixture SQL/Chroma (hoặc fakes thực hiện ownership boundary) đi qua `AnswerQuestionUseCase` → `LegacyReActAdapter` → `RetrieveEvidenceUseCase` → `DocumentAccessPort`; bổ sung HTTP chat test với cookie của A và document của B.
2. Assert provider **không được gọi** khi request truy cập document của user khác ở API (`open_document`/owned path). Ở mức retrieval contract, assert retriever không được gọi khi ownership fail.
3. Assert không truy xuất evidence, không ghi note, quiz/progress hoặc side effect vào tài khoản B. Kiểm tra A→logout→B trên cùng browser/session nếu cần regression.
4. Không lộ lý do tài liệu tồn tại hay không tồn tại trong HTTP response. `AUTH_SCOPE` chỉ là nhãn **nội bộ** của evaluation fixture; test ngoại tuyến có thể phân loại dựa trên expected fixture, không cần thay public domain exception để phân biệt user B.
5. Kiểm tra LLM/tool injection: tài liệu chứa câu lệnh giả mạo quyền, nhưng không được override authenticated `AppContext`.

**Test Lead cases:** `TC-SEC-01` foreign document chat 404/no evidence; `TC-SEC-02` foreign note/quiz side effects = 0; `TC-SEC-03` retriever not called on unauthorized scope; `TC-SEC-04` A/B simultaneous requests isolated; `TC-SEC-05` injected PDF cannot call foreign document.

**Done:** có regression API/integration thực sự, pass trên CI; không khẳng định security gate chỉ bằng synthetic precheck.

### QA-03 — Tool selection: loại bỏ vacuous success [P1]

**Evidence:** [`evaluation/scoring.py#L43-L50`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/scoring.py#L43-L50) dùng `all(...)` trên `tool_calls`.

**Tech implementation:**

- `allowed_tools` chỉ cho biết tên tool nào **được phép** gọi; **không** cho biết tool nào **bắt buộc** để đáp ứng intent. Bổ sung label độc lập `required_tools: tuple[str, ...] = ()` và validation `required_tools ⊆ allowed_tools` trong [`evaluation/schema.py`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/schema.py).
- `tool_calls == ()`: đặt `tool_selection_allowed = None` (không có call để validate) và tính riêng `required_tool_coverage = 0` **chỉ** với variant có tool và case yêu cầu tool. Với `rag_only`, required tool coverage phải `N/A` (không phạt baseline không có tools).
- `tool_calls != ()`: `tool_selection_allowed = float(all(call.name in allowed_tools ...))`; báo cáo `required_tool_coverage` bằng số required tool đã gọi / tổng required tool; `tool_validation_rate` vẫn unknown nếu chỉ có text legacy, không coi `not_observed` là valid.
- Đảm bảo khi tool lỗi/unknown `name`, metric không tự động thành success.

**Test Lead cases:** `TC-TOOL-01` ReAct cần `search_docs` nhưng không gọi -> coverage 0; `TC-TOOL-02` chỉ gọi allowed -> allowed=1; `TC-TOOL-03` gọi unknown -> allowed=0; `TC-TOOL-04` RAG-only no-tool -> N/A; `TC-TOOL-05` legacy unobserved validation -> `None`.

**Done:** không có false positive do `all([])`; KPI phân biệt *selection*, *schema validity*, *tool success*.

### QA-04 — Chính sách đo multi-search và citations [P1]

**Evidence:** [`evaluation/scoring.py#L18-L24`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/scoring.py#L18-L24) chấm `retrieval_calls[0]`; [`LegacyReActAdapter`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/backend/src/study_supporter/orchestration/legacy_react/adapter.py) đã ghi đủ ordered calls và union evidence.

**Tech implementation:**

1. Giữ **initial retrieval** metrics để so sánh fixed-retrieval với Agent: `initial_hit_rate_at_k`, `initial_recall_at_k`, `initial_mrr_at_k`.
2. Thêm **multi-step retrieval success**: `any_search_hit` và `union_evidence_recall` trên distinct chunks (không gọi union là top-k ranking); chỉ tính khi có relevant gold.
3. Nếu muốn `final_context_recall_at_k`, phải bổ sung instrumentation cho context thực sự được cung cấp cho final answer; **không suy đoán** từ all-retrieved evidence.
4. Tách `retrieved_evidence` khỏi `supporting_citations` trong telemetry về sau. Hiện tại `AgentResult.evidences` là union của các search đã chạy, **chưa phải chứng minh các đoạn được trích dẫn hỗ trợ claim** (QA-08).
5. Báo cáo mỗi `retrieval_call` có thứ tự, top_k, chunk_ids; update doc mô tả policy; so sánh case-level, tránh ghi nhận một successful retry bằng điểm ranking giả.

**Test Lead cases:** `TC-RETR-01` first empty, second relevant -> initial hit 0, any-search-hit 1; `TC-RETR-02` two calls cùng chunk -> union đếm 1; `TC-RETR-03` first relevant, second irrelevant -> initial hit 1; `TC-RETR-04` không có tool search -> proper 0/N/A theo case.

**Done:** reproducible per-call/aggregate metrics; không gộp lẫn hit/ranking/citation-support.

### QA-05 — Golden structural evaluation & CI gate [P1]

**Evidence:** [`.github/workflows/quality.yml`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/.github/workflows/quality.yml) chạy `python -m evaluation.runner_v2 --repetitions 3`; hiện kiểm tra runner/test nhưng chưa có chính sách pass/fail dựa trên baseline metric đã chấp thuận.

**Tech + QA implementation:**

- Viết `evaluation/gates.py` (hoặc `scripts/check_eval_gates.py`) đọc JSON output + versioned `evaluation/golden/v1.json` chỉ chứa **ngưỡng structural synthetic**, không phải performance chất lượng LLM.
- Đề xuất deterministic gates: `n_total` khớp expected; expected scope denials đều được ghi và không side effects; không có `unexpected_error`; test metrics semantic fixtures đạt giá trị đã xác minh; `n_unknown` bắt buộc không bị ép thành 0; manifest có commit/dataset/source/prompt hashes.
- Không cứng hóa ngưỡng chất lượng/latency thật trên CI ngắn chạy mock; **real-model comparative evaluation** là manual/nightly và có signoff riêng.
- Upload sanitized result/summary artifact ngay cả khi gate fail (`if: always()`), tránh lộ PII, PDF, prompt, secrets.
- Kiểm tra lỗi parse/reporting làm exit code khác 0; giữ reproducibility cố định theo dataset hash và metric schema version.

**Test Lead cases:** `TC-GATE-01` golden pass; `TC-GATE-02` cố ý đổi metric sai -> CI fail; `TC-GATE-03` thiếu một expected case -> fail; `TC-GATE-04` expected vs unexpected error phân biệt; `TC-GATE-05` không network trong offline tests.

**Done:** CI phát hiện regression cấu trúc; không tuyên bố CI này đo chất lượng model thực.

### QA-06 — Đếm expected denial và unexpected failure riêng [P2]

**Evidence:** [`evaluation/runner_v2.py#L93-L108`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/runner_v2.py#L93-L108) ghi `status="error"` cho cả expected `AUTH_SCOPE`; [`evaluation/scoring.py#L65-L70`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/scoring.py#L65-L70) tính tất cả là `n_failed`.

**Tech implementation:** giữ raw event status để không phá tương thích, nhưng summary có `n_expected_denied`, `n_unexpected_failed`, `n_completed`, `n_incomplete`; mọi dòng phải được phân nhóm đúng một nhóm. Report rõ `expected_error_match` cũng có failure nếu không thấy expected error. Không được coi expected denial là provider failure.

**Test Lead:** trong fixture 15-case × 2 variants × 3 repeats, số bản ghi nên mô tả tường minh: `90 total = 78 completed + 12 expected AUTH_SCOPE`, `0 unexpected failures` **nếu kết quả lần chạy thực tương ứng**; không coi 12 expected denials là bất ổn ứng dụng.

### QA-07 — Cô lập thực nghiệm online [P2, trước baseline thực]

**Evidence:** [`evaluation/runner_v2.py`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/runner_v2.py) nhận arbitrary variant callbacks; [`evaluation/README.md`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/README.md) đã ghi rõ không tự xác thực environment.

**Tech implementation:**

- Tạo dedicated online fixture factory: user/document SQL + Chroma snapshot, độc lập `variant × repetition`, reset chat history/note/progress hoặc clone fixture trước mỗi run.
- Freeze provider/model/temperature, prompt/version hash, embedding/index hash, top-k, hardware, DB revision; log elapsed/tokens/cost khi provider thực sự hỗ trợ, unknown → `null`.
- Tách ingestion/index cost khỏi answer latency; randomize run order + ghi warm/cold/cache policy. Seed runner **không** đảm bảo model deterministic.
- Không thực thi các mutating tools với account thật; cần stub/sandbox và hậu kiểm no side effects.

**Test Lead:** cùng case cùng initial state giữa variants; assert no note/progress carry-over; benchmark 3 repetitions/variant khi model stochastic; paired confidence interval và logs có full manifest.

### QA-08 — Không đồng nhất retrieved evidence với citation support [P2]

**Evidence:** [`LegacyReActAdapter`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/backend/src/study_supporter/orchestration/legacy_react/adapter.py#L29-L79) thu union evidence, [`AnswerQuestionUseCase`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/backend/src/study_supporter/application/use_cases/answer_question.py) chỉ xác minh document scope.

**Tech implementation:** ở phase citation quality, lưu riêng `retrieval_candidates` và `answer_citations`; xác minh citation ID được truy xuất, thuộc user và trang hợp lệ; với claim support phải có kiểm định deterministic/human/judge độc lập. Không yêu cầu thay HTTP DTO ngay trong fix P1, nhưng docs không được gọi citation scope validity là citation precision.

### QA-09 — Đủ coverage để chốt Phase 1 [P2, gate riêng]

**Evidence:** [`evaluation/datasets/v1/README.md`](https://github.com/ManhT005/self-study_supporter/blob/679665b7d14c0d005d8a63724c649ca5957ddd4f/evaluation/datasets/v1/README.md) mô tả smoke 15 cases, chỉ development và không có quiz/personalized.

**Tech + QA:** mở rộng ≥100 approved, independently annotated cases; đủ 7 strata như roadmap, thêm prompt injection, long PDFs/real hybrid/BGE-M3, user history/quiz fixtures, splits theo document/topic và frozen holdout. Reviewer mù biến thể, disagreement resolution, judge parse failure denominators, paired stats. Không đánh dấu Phase 1 DONE trước khi có evidence thực.

---

## 4. Phân công Tech Lead / Test Lead và đề xuất PR

| PR | Phạm vi code (dự kiến) | Tech Lead chịu trách nhiệm | Test Lead chịu trách nhiệm | Tiêu chí merge |
|---|---|---|---|---|
| **PR-1 `fix/eval-metrics-and-coverage`** | `evaluation/scoring.py`, `evaluation/schema.py`, `evaluation/runner_v2.py`, `backend/tests/unit/test_eval_runner.py`, docs | Metric API, semantic version, tool selection, multi-search policy, count failures | Gold test cases QA-01/03/04/06, review denominators | Không còn metric sai nhãn/false-positive; all offline tests pass |
| **PR-2 `test/eval-scope-and-golden-gates`** | `backend/tests/contract|integration`, `apps/api/tests`, `evaluation/gates.py`, `.github/workflows/quality.yml` | Boundary integration, CI script, safe artifacts | Cross-user, no-side-effects, negative gate fixtures | CI 6-job suite green + golden gate cố ý fail được |
| **PR-3 `feat/eval-online-baseline`** (sau đó) | `evaluation/online_*`, fixture provisioning, reports | Isolated provider/index wiring, manifest/sandbox/cost | ≥100 labels, holdout, repeat runs, blind adjudication | Phase 1 exit gate: signed baseline report |

> Nếu PR-1 quá lớn, tách `QA-01 + QA-03` và `QA-04 + QA-06` nhưng **không merge báo cáo benchmark chính thức khi chưa đóng đủ P1**. Không cần mở PR refactor folder chung hoặc thay LangGraph/LangChain trong fix branch.

### Đề xuất workflow

```bash
# Tạo nhánh mới từ develop sau khi chốt chính sách xử lý nhánh feature hiện tại.
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c fix/eval-metrics-and-coverage
# Code + unit tests + docs; push và tạo PR -> develop.
# Không đẩy trực tiếp lên main hoặc tự merge feature đang review.
```

**Lưu ý nhánh:** vì `feature/ai-eval-foundation` chưa được merge vào `develop` tại commit review, PR fix trên `develop` độc lập sẽ thiếu các file evaluation mới. **Chọn một trong hai cách hợp lệ:** (A) mở nhánh fix từ `feature/ai-eval-foundation`, PR **target feature branch**, sau đó merge feature vào develop khi signoff; hoặc (B) merge foundation có điều kiện vào develop trước, rồi tạo fix PR từ develop và chặn Phase 1 benchmark acceptance cho đến khi các fix hoàn thành. **Khuyến nghị A** để PR dễ review và không tạo phụ thuộc ẩn.

Cách A:

```bash
git fetch origin
git switch -c fix/eval-metrics-and-coverage origin/feature/ai-eval-foundation
# Implement; push; PR base = feature/ai-eval-foundation.
# Khi fix đã được nghiệm thu: PR feature/ai-eval-foundation -> develop.
```

### RACI (trách nhiệm)

| Hoạt động | Tech Lead | AI Engineer | Test Lead | Maintainer |
|---|---|---|---|---|
| Chốt metric definitions / API compatibility | **A** | R | C | I |
| Implement correction + instrumentation | A | **R** | C | I |
| Test design, adversarial + regression | C | R | **A/R** | I |
| CI quality-gate & artifact policy | A | R | **R** | I |
| Review & merge PR | C | R | C | **A** |
| Chốt Phase 1 research baseline | A | R | **A (quality)** | A (release) |

`R` = Responsible, `A` = Accountable, `C` = Consulted, `I` = Informed. Bảng phân công mang tính **đề xuất**, cần team xác nhận owner cụ thể.

## 5. Acceptance checklist cho PR-1/PR-2

**Code & contracts**

- [ ] QA-01: `hit_rate_at_k` và Recall@k chuẩn đúng case multi-hop; metric schema/version được ghi rõ.
- [ ] QA-03: no-tool không được tự tính valid; required vs allowed vs N/A được phân biệt.
- [ ] QA-04: initial retrieval và multi-search/union metrics riêng; test retry và duplicate.
- [ ] QA-06: expected denial không bị báo là unexpected runtime error.
- [ ] API response shape (`answer`, `citations`, `trace_id`) không đổi nếu không có ADR và contract migration.
- [ ] Không đổi embeddings BGE-M3/1024D, SQL/Chroma schema/IDs, legacy tool set/5-iteration baseline, provider selection hoặc frontend feature.

**Testing & security**

- [ ] Ownership cross-user được test qua production-representative API/application/retriever, không chỉ synthetic precheck.
- [ ] Zero foreign evidence và zero unauthorized side effects trong logs/assertions.
- [ ] Deterministic offline test suite không kết nối network; failure injection làm gate fail thật.
- [ ] CI lint/format, backend+API unit/contract/integration, web, docker smoke đều green sau PR.
- [ ] Report/artifacts sanitize dữ liệu: không raw user questions/PDF text, credentials, model hidden reasoning hoặc tool arguments nhạy cảm.

**Documentation & review**

- [ ] Review table gắn testcase ID → bug ID → PR/commit SHA → actual result → reviewer.
- [ ] `evaluation/README.md`, benchmark plan, report schema cập nhật đúng nghĩa metric.
- [ ] Tech Lead xác nhận semantics/compatibility; Test Lead xác nhận negative/regression tests; maintainer đồng ý merge.
- [ ] Có rollback đơn giản: revert PR theo commit; không cần SQL migration hoặc reindex.

### Lệnh kiểm thử tham khảo (tại repository root)

```bash
python -m pytest backend/tests/unit backend/tests/contract apps/api/tests -q
python -m pytest -q
ruff check .
ruff format --check .
python scripts/check_import_boundaries.py
python -m scripts.export_http_contract --check
python -m evaluation.runner_v2 --repetitions 3
# Sau khi bổ sung gate:
python -m evaluation.gates --report data/evaluations/<run_id>/results.json --golden evaluation/golden/v1.json
```

> Đường `evaluation.gates` và `evaluation/golden/v1.json` là **đề xuất chưa có trong commit review**; phải được Tech Lead triển khai trước khi chạy. Nếu CLI hiện tại ghi run_id ngẫu nhiên, script CI cần lấy output path có cấu trúc từ runner thay vì hardcode `<run_id>`.

## 6. Definition of Done / Go–No-Go

### Engineering foundation merge gate (PR-1 + PR-2)

**GO** khi QA-01/02/03/04/05 đã có code/test/golden gate tương ứng; CI fresh green; report metrics không còn misleading; Tech Lead và Test Lead cùng signoff. QA-06 nên hoàn thành nếu không tạo breaking changes.

**NO-GO** nếu: Recall vẫn mang nghĩa hit-rate; empty tool selection vẫn được chấm 1; privacy chỉ được chứng minh bởi synthetic owner precheck; multi-search policy không thống nhất; golden regression không bắt được cố ý gây lỗi.

### Phase 1 benchmark acceptance gate (độc lập, chưa đạt)

**GO** chỉ khi có dataset ≥100 câu được duyệt/annotate độc lập, frozen holdout, production hybrid/BGE-M3 + real provider, aligned configs/cost/latency, repeat runs, judge/human comparisons, confidence intervals, privacy/prompt-injection cases và signed report. Synthetic CLI hay việc GitHub CI green **không thay thế** gate này.

### Quyết định release

Không bật LangChain/LangGraph mới và không đổi production traffic trong PR sửa evaluation. Chỉ bắt đầu POC framework sau khi baseline đã đo được đáng tin cậy; hoạt động nghiên cứu độc lập trên nhánh sandbox có thể tiến hành nhưng **không claim comparative superiority** trước khi vượt Phase 1 gate.

## 7. Handoff template cho mỗi issue/PR

```markdown
### QA-XX — <short title>
- Severity / Type:
- Baseline commit & code line:
- Root cause confirmed vs hypothesis:
- Expected behavior:
- Proposed change (code paths):
- Public compatibility impact: none / documented
- Test IDs + negative cases:
- Actual test commands & evidence link:
- Before/after metric or trace:
- Safety/privacy side effects:
- Reviewer (Tech Lead): [ ]
- Reviewer (Test Lead): [ ]
- Maintainer merge decision: [ ]
```

---

**Tóm tắt:** Ưu tiên sửa **evaluation validity** trước khi phát triển framework mới. Không rewrite architecture vì request-local agent contracts và CI đã có nền tảng tốt. Báo cáo này là **hướng dẫn kỹ thuật và kiểm thử đề xuất**, chưa phải bằng chứng Tech Lead đã triển khai hoặc test độc lập đã chạy.
