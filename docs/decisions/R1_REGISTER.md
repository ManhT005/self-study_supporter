# R1 decisions and change control

Functional SRS approval is recorded in `../srs/baseline.json`. All technical choices below remain OPEN until an approver, date and ADR are recorded. Role labels designate responsibility, not named assignments or signatures. Do not implement a package blocked by its decision deadline.

| Decision | Question | Proposed recommendation from SRS | Owner | Status | Chosen / approver / date / ADR |
| --- | --- | --- | --- | --- | --- |
| DEC-01 | R1 email reminder bắt buộc hay có thể dùng in-app trước? | Bắt buộc một workflow n8n nếu mục tiêu tích hợp; email chỉ khi verified/consent, nếu không → HOLD AUT release | PO + BE | OPEN | Pending |
| DEC-02 | Storage PDF nguồn chọn MinIO hay filesystem private? | Interface ObjectStorePort; dev local filesystem, pilot MinIO/S3-compatible với backup/encryption | Architect + Ops | OPEN | Pending |
| DEC-03 | Session persistence dùng DB hay Redis? | DB-digest session đơn giản cho pilot; Redis cho cache/rate; không lưu duy nhất state không thể phục hồi | Security + BE | OPEN | Pending |
| DEC-04 | Queue chọn Celery hay RQ? | Chọn một broker/worker stack sau spike, ưu tiên dễ test/retry/lease; không thêm Kafka | BE + Ops | OPEN | Pending |
| DEC-05 | API /documents chuyển 201 sync sang 202 async bằng cách nào? | /api/v2/documents cho breaking change; contract migration song song, không âm thầm đổi v1 | API Lead + FE | OPEN | Pending |
| DEC-06 | Retention PDF/chat/history/audit/backup bao lâu? | Chốt product privacy policy trước public pilot; chưa được điền số tùy tiện | PO + Security | OPEN | Pending |
| DEC-07 | Target load profile, RPO/RTO và budget cloud/model? | Profiling M0 + Ops quote; formal signoff ngưỡng trước G7 | Ops + PO | OPEN | Pending |
| DEC-08 | Quiz cho phép thử lại/câu hay chỉ một attempt mỗi issued quiz? | R1 một câu chỉ một lần nộp trong một QuizSet; ôn lại tạo QuizSet mới | PO + BA | OPEN | Pending |
| DEC-09 | Khi citation-support grader không chắc chắn? | Abstain hoặc câu trả lời có giới hạn, không công bố verified | AI Lead + QA | OPEN | Pending |
| DEC-10 | LangChain/LangGraph có nằm trong release? | Không mặc định; disabled POC, bật chỉ khi G5 cho thấy lợi ích | AI Lead + Tech Lead | OPEN | Pending |
| DEC-11 | Rule-based concept signal tính ra sao? | Phiên bản minh bạch count/recency/due, không gọi mastery model; đặc tả công thức trong ADR | BA + Data/AI | OPEN | Pending |
| DEC-12 | Scope xóa: hard delete vs logical delete? | Revoke ngay, cleanup async, audit và retention; quy tắc backup/legal cần duyệt | Security + Data | OPEN | Pending |

## Source metadata discrepancy

The supplied Word source calls v1.0 “Approval”, retains “CHƯA PHÊ DUYỆT” in its front matter, and marks the role matrix “Chốt”. Preserve these statements as source text. The PO's instruction authorizes functional baseline implementation; it is not evidence that DEC-01…12, live benchmarks, specialist release gates or numeric pilot targets have been signed. Source bytes and requirement text were not edited.

## Change request record

CR-ID; reason; before and after; impacted FR/BR/NFR/UAT; API/data/event version and migration; security/privacy; scope/time/cost; tests/evidence; PO/QA/Tech Lead approval; date. No CRs have been approved by this branch.

## Next package

WP-02 default-deny agent writes follows WP-01. WP-03 remains blocked by DEC-03; quiz schema WP-04 requires DEC-08. Keep `/api/v1` synchronous upload status and DTO intact. Optional WP-15/16 remain disabled and off the mandatory path.
