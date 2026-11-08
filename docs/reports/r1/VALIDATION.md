# WP 01 local validation

Date: 2026-11-05. Base: `develop@155fd76c062491254da8b463f8ed3e88e597ded0`. Candidate: `feature/r1-01-baseline-freeze`. These are supporting local results on the working implementation; release acceptance and independent review remain pending. The CI profile artifact records the exact clean candidate SHA after publication.

| Check | Result |
| --- | --- |
| Backend unit and contract suite | 211 passed |
| HTTP API suite | 9 passed |
| Ruff lint and format | PASS |
| Architecture import boundary checker | PASS |
| Source checksums recorded; public ID ownership | PASS: 96 FR, 34 BR, 28 NFR, 26 UAT, 14 UC; full sources private |
| Runtime OpenAPI against committed v1 snapshot | PASS; contract unchanged |
| Synthetic baseline profile, 5 repetitions | PASS: 75 timing spans, 0 span errors; 9 operation types |
| Existing synthetic eval runner, 3 repetitions + structural golden gate | PASS; synthetic evidence only |
| Backend source distribution and wheel build | PASS |
| Real PDF/BGE-M3/provider latency and quality | NOT RUN |
| PostgreSQL / Docker / browser workflows | Hosted CI pending |
| Independent Security/QA/Tech Lead review | Pending |

The profiler shows BM25 construction and two chunk loads on the initial session path, and reuse within the warm session. These observations describe the synthetic lifecycle only. No retrieval/cache/model tuning was introduced. Existing deprecation warnings from PyMuPDF/SQLAlchemy/Starlette remain; no new runtime failure occurred.

The frozen develop baseline has a successful hosted workflow [38580852308](https://github.com/ManhT005/self-study_supporter/actions/runs/38580852308). Candidate hosted status must be checked on its own SHA. G0 is HOLD until the remaining evidence and WP-02 hardening are reviewed. No FR/UAT is marked accepted by these local checks.
