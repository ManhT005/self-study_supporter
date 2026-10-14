# Learning workspace implementation

The user authorized implementation on `feature/ui-learning-workspace` on 2026-10-14.
The supplied playbook and migration plan govern delivery; the archived master plan
and PNG sketches in this directory govern visual design. Its older course-centric
API examples are superseded by the document-first decisions below.

## ADR: executable MVP decisions

- Frontend: Next.js App Router, strict TypeScript, npm with one lockfile, Tailwind,
  Radix accessible dialog primitives, Lucide icons, Zod and TanStack Query. Light
  theme, Vietnamese interface; desktop sidebar and four-item mobile bottom nav.
- Domain: document-first workspace. “Môn học” links to `/documents`; no Course
  schema, fabricated goals, mastery, streaks, schedules or recommendations.
- Auth: random opaque HttpOnly cookie, SameSite=Lax, Secure by default; exact
  configured Origin required on every write including login. Tokens stored only
  as SHA-256 digests in bounded process memory. Eight-hour absolute expiry,
  revoke/rotate at login and logout. Restart logs everyone out. Single API worker
  only; durable/multi-replica sessions require a separate additive migration.
  Local HTTP explicitly opts out of Secure. Auth attempts limited by client IP;
  proxy does not trust browser-supplied forwarded identity headers.
- Ingestion: synchronous response, one active ingestion per process, 20 MB PDF
  limit. Work runs off the event loop. Pending UI shows no invented percentages.
  A failed upload can be retried by uploading the same file (existing hash policy).
  No queue/resume promise. On single-writer startup, stale processing records are
  marked failed through an application facade; client reloads status after a
  connection interruption. No temporary upload files are introduced.
- Chat: synchronous JSON from a fresh principal/document-scoped LearningSession;
  citations come exclusively from returned Evidence. Reader uses indexed text
  with actual page bounds: original PDF bytes are not currently persisted.
- Quiz: answers remain server-side in a bounded expiring session-owned store;
  question submission is idempotent while the quiz remains in that store. Attempts
  persist using the existing progress use case. Restart expires unfinished quizzes.
- API: `/api/v1`, dedicated DTOs, uniform `code/message/request_id` errors;
  runtime OpenAPI snapshot generates frontend types. Ownership failures return
  404. No wildcard CORS. Provider errors expose no internal exception text.
- Deployment: additive preview Compose on isolated data; existing Streamlit stack
  retained until restore/rollback and real-provider acceptance gates pass. Never
  run both writers on the existing Chroma path.

## Routes and legacy inventory

| Route / behavior | Legacy adapter | Application mapping | Evidence |
| --- | --- | --- | --- |
| `/login`, `/register`, logout | components/auth.py | Authentication | API session/expiry/origin tests |
| `/dashboard`, `/documents`, upload | components/sidebar.py | OwnedDocuments, IngestDocumentUseCase | ownership, ingestion and API tests |
| `/documents/:id/study` | components/chat.py | LearningSession.answer | scope, empty retrieval, citation tests |
| `/practice` | components/quiz_arena.py | generate_quiz, submit_quiz | quiz validation, submission/API tests |
| `/progress` | router.py | GetProgressUseCase | persisted principal-scoped summary |
| `/documents/:id` | components/graph_viewer.py | LearningSession.build_graph, learning_path | graph empty/cycle tests |
| `/settings`, provider selection | components/sidebar.py | ApplicationFactory.provider(mode) | provider tests |
| Save note in study | save_note tool | LearningSession.save_note | notes isolation tests |

Unsupported product expansion (course CRUD, flashcards, schedules, mastery,
document deletion, memory management, durable quiz transcripts, SSE) stays outside
this migration's feature-parity scope. No inert controls for those features.

## Acceptance and release gates

- Baseline: 122 offline Python tests passed (outside Windows filesystem sandbox).
- Each implementation checkpoint records validation and a separate commit.
- Synthetic API/browser tests must cover login → upload → ready → question →
  evidence → quiz submission → progress, cross-account access and logout.
- Real PDF/provider/model acceptance, PostgreSQL integration, original-data
  backup/restore and traffic rollback must pass before production cutover or
  Streamlit removal. Synthetic doubles cannot establish these operational gates.

Implementation validation and remaining gates are recorded in `VALIDATION.md`.
