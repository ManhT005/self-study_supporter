# Post-merge live evaluation implementation — 2026-10-14

Branch: `feature/ai-online-eval-baseline`, from `develop`
`79224d718ce154fbb1a2222fc9c5955e64ae4480`. The
[execution plan](../../plans/ai-modernization/09_POST_MERGE_AI_EXECUTION_PLAN.md)
is implemented through label-validation tooling, isolated live callbacks and
blinded review export. This is engineering evidence, not Phase 1 acceptance.

## Reviewable commit slices

| Commit | Delivered |
| --- | --- |
| `b621b5b` | Merge-SHA/CI rebaseline, execution plan and gate evidence |
| `2d54d44` | Independent v2 annotations, adjudication, source/index/page/quote validation and split leakage checks |
| `5ff9136` | Real SQL/BGE-M3/hybrid/full four-tool ReAct versus RAG-only harness, isolated snapshots, bounded requests and private review export |
| `af7373a` | Sanitized numeric HTTP status and known error types |
| `33068eb` | Explicit Flash-Lite 3.1 model pin, minimal thinking and recorded configuration |

Application API/frontend, retained SQL/Chroma, embedding dimensions, production
provider selection and legacy parser/prompt/tool order were not changed. No
LangChain/LangGraph adapter, release cutover, GitHub push or phase approval occurred.

## Approved private source and isolation

The user-selected PDF `data/cnn-nhan dang bien so.pdf` was ingested by the actual
production pipeline into a new isolated SQLite/Chroma snapshot: 58 pages, 61 chunks.
Its already-computed vectors were copied to a second synthetic account for the
foreign-document scope probe. This is one quality source, not two independent
documents. Preparation made zero cloud model calls.

Runtime: existing `self-study-supporter:local` image, Python 3.11.17,
`google-genai==1.56.0`, local BGE-M3 cache revision
`5617a9f61b028005a4858fdac845db406aefb181`, 1024 dimensions, SQL revision `p0_0001`,
Dense/BM25/RRF with `rrf_k=60`. Repository and model cache were mounted read-only;
only `data/eval_private/v2` was writable. No application storage volume was mounted.
Each variant/sample used a fresh clone and subprocess. After the final run,
snapshot hashes verified unchanged and no temporary work leases remained.

The extracted PDF has legacy font substitutions; no OCR/normalization or retrieval
algorithm change was introduced. Three private cases are explicitly unreviewed
engineering smoke labels: factual, unanswerable and foreign ownership. They do
not meet G1 independent-annotation, seven-stratum or grouped-split requirements.

## Real Gemini attempts and bounded recovery

The user requested Gemini with few free-tier requests. The entire investigation
was capped at six generation attempts, including diagnostic calls. SDK retries
were disabled; no within-run model fallback occurred. Output cap was 768 tokens
for live samples, input cap 24,000 characters, answer deadline 90 seconds and
worker deadline 180 seconds. A tiny standalone diagnostic used only eight output
tokens. Read-only model metadata requests are separate from generation attempts.

| Run / operation | Model | Attempts | Actual outcome |
| --- | --- | ---: | --- |
| `2c718e4171984140b802042e44627fd1`, SHA `5ff9136` | `gemini-2.5-flash` | 1 | First request failed; further calls blocked. Six records: four unexpected provider failures, two correct scope denials |
| `239d866f89884692a240d23c9e8b860e`, SHA `af7373a` | `gemini-2.5-flash` | 1 | Same blocking behavior; sanitized telemetry identified HTTP 404 / ClientError |
| Tiny availability diagnostic | `gemini-2.5-flash` | 1 | HTTP 404; classified message contains “no longer available”, despite the model appearing in metadata |
| `c13971026cc2491a882cff5c230c03e0`, SHA `33068eb` | `gemini-3.1-flash-lite` | 3 | Two-case paired smoke completed; engineering gate passed |
| **Total** | | **6** | No further generation attempts |

The last run explicitly pinned a different model in a separate manifest and used
`thinking_level=minimal`, `include_thoughts=false`, temperature zero. Google lists
[Flash-Lite 3.1](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite),
its [thinking setting](https://ai.google.dev/gemini-api/docs/gemini-3) and
[free-tier pricing](https://ai.google.dev/gemini-api/docs/pricing). Account quotas
and actual billing remain outside this report; no cost amount was inferred.

To stay within the remaining three attempts, the final smoke selected only the
factual and scope cases. The unanswerable case has not completed on the new pin.
That limits G2 evidence; it is not an accepted full three-case dry run.

| Final factual sample | Attempts | Answer latency | Candidate chunks |
| --- | ---: | ---: | ---: |
| Legacy ReAct, full production four-tool prompt | 2 | 30,559 ms | 3 |
| RAG-only | 1 | 5,648 ms | 3 |

Both returned answers containing the expected year; this simple engineering
observation is not independent factual/citation adjudication. Both scope records
returned expected `AUTH_SCOPE` with zero model calls. Final accounting: four
records, two completed, two expected denials, zero unexpected failures. Both
successful samples observed model version `gemini-3.1-flash-lite`.
Prompt digest: `54d79a0d3e9613673421154c427fa407ab4afe46926b0cc0a1a725f0d57f5968`.
Source hash: `sha256:8694b52da355d5915480383d23c0d630bf51dcf563de2951d7eea9d71581440f`.
Index hash: `18b0b523aef56ede654fc7936f0dd8ca5565f4f3ae97ca2202ff691b1727af97`.

The two factual latencies are single observations, excluding separate embedding
warmup and fixture provisioning. They do not establish production p50/p95 or a
quality difference. Aggregates that include scope denials must not be represented
as answer latency benchmarks. Alias versions are not immutable provider digests.

Sanitized reports and private answers remain under ignored
`data/eval_private/v2/runs/<run_id>/`. The final blinded export contains two packets,
zero missing answers, one expected-denial case and `reviewed=false`. Assignment
maps remain separate/private. No reviewer scores or supporting citations were
invented. The temporary credential environment file was removed after each run;
no key, raw SDK exception, source text or answer was committed.

## Fresh local checks

At implementation SHA `33068eb` on Windows/Python 3.12.7:

- Backend unit/contract plus API: **212 passed**, 63 dependency deprecation warnings.
- Ruff check/format: passed, 194 Python files formatted.
- Import boundary and runtime OpenAPI snapshot: passed.
- Synthetic golden: passed; 90 records, 78 completed, 12 expected denials,
  zero unexpected failures. Run `be336317418b4fbf985be726cf2c5c9e` at `af7373a`.
- Real final two-case live engineering gate: passed; immutable snapshot verified.

No fresh remote CI, PostgreSQL integration or frontend/browser execution is claimed
for this branch. Successful CI on the original merge SHA is documented separately
in [post-merge rebaseline](POST_MERGE_BASELINE.md).

## Remaining execution gates

G0 needs independent signoff. G1 needs ≥100 approved, independently annotated
cases across seven strata and separated topics/documents/splits; the validator is
ready, but one approved PDF cannot supply the required independent sources.
G2 needs the full factual/unanswerable/scope dry run and reviewer acceptance on
the chosen pin. G3 needs paired repetitions, quality/abstention/quiz/personalized
grading, citation-support adjudication and independent blinded review.
Chat-memory fixtures remain unsupported by the current AgentPort and are rejected.
Human approval is never substituted by the structural/live engineering gate.

M4 LangChain and M5 adoption decision remain gated by G3. UI real-provider,
historical restore, rollback and physical-device checks remain separate. See
[implementation status](../../plans/ai-modernization/IMPLEMENTATION_STATUS.md)
and [live usage](../../../evaluation/live/README.md).
