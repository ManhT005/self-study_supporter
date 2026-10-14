# Phase 1 — Legacy Baseline & Evaluation Foundation

**Priority:** P0/blocker · **Estimate:** 1–2 weeks (2 engineers) · **Depends on:** UI preflight, pinned branch SHA.
**Do not change agent algorithm, embedding model, vector dimension, existing SQL/Chroma structures during this phase.**

## 1. Acceptance inputs and freeze

- [ ] Record `git rev-parse HEAD`, branch, Python/Node versions, model/provider IDs, prompt digests, embedding version, database/Alembic revision, Chroma names and hardware.
- [ ] Verify existing 128 backend/API tests and 12 frontend tests as **previously reported**, then rerun current branch CI and record actual fresh results; do not carry forward counts blindly.
- [ ] Close or explicitly exclude the pending UI real-provider, restored historical SQL/Chroma, rollback and physical-device gates in `docs/design/ui-v1/VALIDATION.md`.
- [ ] Snapshot/backup using existing runbooks before online evaluations. Evaluation accounts must contain synthetic/approved PDFs only.
- [ ] Baseline variants: `rag_only` (original hybrid retriever + answer prompt) and `legacy_react` (original five-iteration tool loop) against **identical** data/model/settings.

## 2. Dataset design

Create versioned data under `evaluation/datasets/v1/` **without committing private PDFs or secret labels**. Store document hashes and fixture generation scripts in git; private assets under ignored `data/`.

**Proposed v1 target: 120 independently labeled questions** (expand if CI/reviewer time allows):

| Stratification | Example | Count |
|---|---|---:|
| Single-chunk factual | explicit definition and formula | 30 |
| Multi-hop across pages | combine two sections | 20 |
| Vietnamese domain synonyms | phrase drift, abbreviations | 20 |
| Missing evidence / unanswerable | unrelated fact, absent topic | 15 |
| Quiz intent and content coverage | request N valid questions from a selected topic | 15 |
| Personalized / progress-dependent | use stored attempts/notes correctly | 10 |
| Unsafe cross-document / tenant probe | attempt to retrieve B's document, prompt injection in PDF | 10 |
| **Total** | | **120** |

Use at least 3–5 documents, include long/multi-page and Vietnamese accents, blank/corrupt PDF cases in separate ingestion regression suite. Annotate `expected_doc_ids`, relevant `chunk_ids`, expected answer facts, `must_abstain`, allowed tool names, difficulty, `requires_history`, expected concept IDs, labeler/consensus. Split 70% development / 15% validation / 15% frozen holdout **by document/topic** where possible to reduce leakage; do not tune prompts against holdout.

**Schema sketch:**

```json
{
  "case_id":"FACT-001", "category":"factual", "question":"...",
  "user_fixture":"user_a", "document_set":"set_v1",
  "expected_doc_ids":["doc_a"], "relevant_chunk_ids":["chunk_12"],
  "reference_facts":["..."], "must_abstain":false,
  "allowed_tools":["search_docs"], "requires_history":false,
  "source_hash":"sha256:...", "annotation_version":"v1"
}
```

## 3. Runner refactor — exact locations

Observed in `evaluation/runner.py`: existing opt-in entrypoint slices `load_eval_dataset(... )[:5]`. **Remove this hardcoded five-case slice in the new runner** and provide `--limit` explicitly for smoke tests. Existing `evaluation/eval_runner.py` measures runtime and tool names but is not a fully versioned comparative framework.

Proposed additions:

```text
evaluation/
  datasets/v1/README.md + *.jsonl + fixtures/
  baselines/legacy_runner.py
  adapters/{rag_only,legacy_react,langchain_agent,langgraph}.py
  score/{retrieval,answer,tooling,quiz,privacy}.py
  runner_v2.py
  reports/README.md                # templates only; generated results ignored
backend/tests/unit/test_eval_schema.py
backend/tests/contract/test_agent_result.py
```

Run record must contain: `case_id`, `variant`, `run_id`, Git SHA, prompt hash, model ID/version, embedding/index hash, `top_k`, seed/temperature where supported, retrieved ordered chunk IDs, tool call names/validated args (redacted), `citations`, step counts, total/token latency, model usage/cost estimate, structured errors, grade and judge metadata. **No full PII, raw hidden thought, API key or user PDF text in shared logs.**

## 4. Metric definitions and failure classes

| Metric | Definition | Source |
|---|---|---|
| Hit Rate@k | fraction of gold-labeled cases with at least one relevant chunk in top-k | gold chunk labels |
| Recall@k | distinct relevant chunks in top-k / all distinct gold relevant chunks, averaged over eligible cases | gold chunk labels |
| MRR@k | reciprocal rank of first relevant chunk averaged over cases | ordered retrieval |
| nDCG@k | gain-discounted relevance, normalized to ideal ranked list | graded relevance judgments |
| Citation precision | cited evidence pieces that directly support claims / all cited pieces | manual adjudication |
| Citation coverage | answerable cases with at least one *correct* supporting citation | manual/evidence check |
| Abstention correctness | unanswerable cases that decline unsupported claims / unanswerable cases | case labels |
| Valid tool call rate | successful JSON-schema+permission validations / attempts | trace records |
| Tool selection accuracy | turns whose tool set meets the expected capability / labeled turns | category labels |
| Required tool coverage | required tool names called / required names, for tool-capable variants only | required vs allowed labels |
| Quiz exactness | generated sets satisfying count, four distinct options, one correct index, support | schema + human check |
| Latency p50/p95 | request elapsed time in ms, per variant and hardware/model | monotonic timing |
| Cost | input/output tokens or estimated local compute per completed case | provider telemetry |

LLM-as-judge can help assess faithfulness/relevance but is **secondary** to deterministic structural checks and a blind human-labeled sample. In `evaluation/metrics.py`, score-parse failures are already tracked; ensure they do not silently become “success” or disappear from denominators. Report both `n_valid` and `n_failed`.

Metric schema version 2 implements these corrected definitions; version 1's
`recall_at_k` was Hit Rate@k. Initial-call ranking includes empty retrievals;
`any_search_hit` and distinct `union_evidence_recall` measure later searches
separately without inventing a union top-k rank or final-answer context.
Expected fixture denials and unexpected failures have separate summary counts.

## 5. Fair experimental protocol

1. Freeze model, temperature or deterministic settings, prompt, reranker flags, dataset/document IDs and index. Run paired RAG-only / legacy ReAct, randomize variant order and separate cache effects.
2. Execute each online case ≥3 repetitions if stochastic. Estimate 95% bootstrap confidence interval for paired deltas (not just means).
3. Human reviewers blind to variant label assess a preselected 20–30 item stratified subset; report disagreement with judge and resolution policy.
4. Store errors as typed categories: `NO_EVIDENCE`, `INVALID_TOOL`, `INVALID_SCHEMA`, `TIMEOUT`, `AUTH_SCOPE`, `PROVIDER_ERROR`, `RETRIEVAL_EMPTY`, `QUIZ_INVALID`, `INTERNAL`.
5. Log results to ignored `data/evaluations/<run_id>/` + publish safe Markdown summaries `docs/reports/ai-eval/<date>-baseline.md` after review.
6. CI only runs synthetic unit/contract/golden regression set. Heavy model or GPU jobs are opt-in/manual/nightly when infrastructure is available; they must not block routine PRs on lack of external credits.

## 6. Key tests (example IDs)

- `BL-01`: variant runs identical questions/document snapshot/provider configuration.
- `BL-02`: no relevant document → abstention, no invented citation.
- `BL-03`: account A query with B's ID → no B evidence, no side effects.
- `BL-04`: PDF with instruction to ignore safety → document text treated as data only.
- `BL-05`: tool count/latency/cost computed with explicit denominators and per-case failure.
- `BL-06`: repeated runs reproducible with pinned dataset/config manifest.
- `BL-07`: every citation maps to an owned document and existent page/chunk.
- `BL-08`: invalid quiz/JSON cannot be accepted by grader.
- `BL-09`: mock tests have zero provider/network calls on import.
- `BL-10`: regression against baseline snapshot after future feature-flag swaps.

## 7. Gate / exit evidence

**Must-have:** validated ≥100-case dataset with stratification; locked holdout, comparison table, metric definitions, failure taxonomy, sanitized raw trace references, reproducibility manifest and human review. No claim of “LangGraph is better” yet. Create a baseline report listing the exact model, sample counts, costs and confidence intervals. Keep the original evaluation logic accessible for historical comparison.

**Next phase:** [`01_LANGCHAIN_POC.md`](01_LANGCHAIN_POC.md) starts only after baseline runner can call arbitrary variant adapters without mutating UI state.
