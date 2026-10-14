# Evaluation foundation and opt-in historical baseline

No evaluation module runs a network call on import or during default pytest.

Run the versioned, synthetic contract smoke without models, SQL or Chroma:

```powershell
.venv/Scripts/python -m evaluation.runner_v2 --repetitions 3
.venv/Scripts/python -m evaluation.runner_v2 --limit 3
.venv/Scripts/python -m evaluation.runner_v2 --repetitions 3 --report-path-file data/evaluations/report-path.txt
.venv/Scripts/python -m evaluation.gates --report-path-file data/evaluations/report-path.txt --golden evaluation/golden/v1.json
```

The default runs all selected cases. `--limit` explicitly samples the first N cases;
`--split` defaults to development, so holdout is not silently used. Source/dataset
hashes, Git SHA/dirty state, prompt digests, settings and environment accompany each
ignored `data/evaluations/<run_id>/results.json`. Variant order is randomized with a
fixed seed; each case/repetition is independent. The CLI uses a lexical retriever and
an echo fixture with a **search-only** ReAct prompt. It checks contracts, pairing and
scope denial; it does not benchmark the production four-tool agent or AI quality.
See [dataset provenance and gaps](datasets/v1/README.md).

`run_comparison(cases, variants, manifest)` accepts arbitrary callbacks returning the
framework-independent `AgentResult`, including `RagOnlyAdapter` and
`LegacyReActAdapter`. Live callbacks must bind identities from approved fixture
accounts, construct fresh request-scoped tools, isolate history and mutating tools
between variants/repetitions, pin the same provider/model/document/index, and supply
an accurate `execution_mode="online"` manifest. An opt-in [live CLI and isolated fixture preparation](live/README.md) now use the
production pipeline with bounded Gemini requests. Independent [v2 labels](datasets/v2/README.md)
and external gate approvals remain required for benchmark mode. The historical
command below remains available. The harness checks source/prompt coverage but
cannot verify a caller's infrastructure
declarations or eliminate provider stochasticity. Its seed controls evaluation
order/bootstrap, not provider sampling.

New manifests declare `metric_schema_version="2"`. **Version 1's `recall_at_k`
was hit rate, not standard recall; do not compare it to version 2 recall.** Historical
reports remain unchanged. Version 2 keeps hit rate as `hit_rate_at_k`, calculates
Recall@k as distinct relevant top-k chunks / all distinct relevant chunks, and
retains MRR/nDCG with rank-preserving duplicate suppression. Empty gold is N/A.

`initial_*` metrics describe the first recorded retrieval call, including an empty
call; the unprefixed ranking keys alias this initial policy. Without call telemetry,
the first k returned evidence items are the fallback. `any_search_hit` uses all
recorded searches (or all returned evidence when call telemetry is absent).
`union_evidence_recall` uses distinct returned evidence without a top-k cap.
Retries never inflate initial ranking scores. Failed tool invocations remain a
legacy measurement limit; the recorder currently captures completed retrieval calls.
Final-answer context coverage is not inferred from the evidence union.

Cases distinguish `required_tools` from `allowed_tools`, with required ⊆ allowed.
Manifest `tool_capabilities` declares tool-capable variants. Empty tool calls yield
`tool_selection_allowed=null`; required coverage is zero when a declared tool-capable
variant omits a required tool. RAG-only required-tool coverage is N/A and has zero
eligible cases. Undeclared capabilities remain unmeasured. Name selection, required
coverage and observed schema validation are separate metrics; legacy validation,
refusal, token usage and cost remain null.

Summary groups partition all records into `n_completed`, `n_expected_denied`,
`n_unexpected_failed` and `n_incomplete`. A missing expected denial is an unexpected
failure even when the raw status is completed. For compatibility, `n_valid`/`n_failed`
retain raw completed/error status counts; raw `n_failed` includes expected denials
and must not be used as application error rate. Retrieval failures score zero on
gold-labeled cases. Per-metric eligible/observed/unknown denominators and paired 95%
bootstrap intervals remain explicit; repetitions are averaged per case before
resampling cases. These intervals describe structural metrics only.

`retrieved_evidence` contains candidates, while `supporting_citations` remains null
until independently assessed. The legacy telemetry `citations` key aliases the
candidate evidence for compatibility; the public HTTP DTO is unchanged. Citation
scope validity checks document membership, not claim support or citation precision.

Raw records exclude question/answer/document text, filenames, model reasoning,
tool arguments and exception strings. A hash replaces the answer, and safe citation
IDs/pages, tool names and error codes support diagnostics. See [report policy](reports/README.md).

Default pytest covers fake-provider regression/schema/scoring tests. CI also runs
the synthetic CLI and a [versioned structural golden gate](golden/README.md), retaining
the sanitized artifact even on failure. The gate checks the frozen manifest,
every case/variant/repetition, record-level scores, recomputed summary/paired stats,
candidate provenance, expected vs unexpected outcomes, and independent semantic
fixtures. It exits nonzero for corrupt/missing data or violated expectations.
The golden applies to the full 15-case, three-repetition run; `--limit` is a smoke
option and deliberately fails that full-run membership gate.

Authorization coverage also exercises real SQL ownership through the application,
legacy adapter and retrieval boundary, plus authenticated HTTP foreign chat/note/quiz
requests with provider/vector/write assertions. A deterministic adversarial provider
tests forged identity arguments after injected document text reaches its prompt.
This proves the scoped boundary for those scripted cases, not general real-model
prompt-injection robustness or real Chroma integration. Independent ≥100-case
labels, frozen holdout, real-model repetitions, blinded review and operational UI
gates remain required by the [roadmap](../docs/plans/ai-modernization/README.md).

Use a dedicated synthetic account with a ready owned document:

```powershell
python -m evaluation.runner --user-id 123 --dataset data/eval_dataset.json --output data/eval_results.json
python -m evaluation.runner --user-id 123 --limit 5 --model qwen3:1.7b
python -m evaluation.run_judge
python -m evaluation.metrics
```

The comparison preserves the original RAG-only prompt, hybrid ranking and ReAct
iteration/tool metrics, with personalized history only for personalized questions.
The judge and similarity commands consume models and write under ignored `data/`.
Scores from the small Ollama judge are exploratory, not an accepted quality benchmark.
The historical runner now evaluates the full JSON dataset unless `--limit` is
explicit, honors the configured Ollama model unless `--model` is supplied, and
generates RAG-only from the same single retrieval whose IDs it records. Existing
JSON output and personalized-history semantics remain available. Judge summaries
retain missing, malformed and out-of-range scores as failures in their denominators.
`eval_test.py` remains a command redirect to `evaluation.runner`.
