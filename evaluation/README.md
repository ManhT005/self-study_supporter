# Evaluation foundation and opt-in historical baseline

No evaluation module runs a network call on import or during default pytest.

Run the versioned, synthetic contract smoke without models, SQL or Chroma:

```powershell
.venv/Scripts/python -m evaluation.runner_v2 --repetitions 3
.venv/Scripts/python -m evaluation.runner_v2 --limit 3
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
an accurate `execution_mode="online"` manifest. V2 has no live CLI or automatic
fixture provisioning yet; the historical command below remains available. The
harness checks source/prompt coverage but cannot verify a caller's infrastructure
declarations or eliminate provider stochasticity. Its seed controls evaluation
order/bootstrap, not provider sampling.

Metrics have explicit `n_total`, `n_valid`, `n_failed`, `n_incomplete` and per-metric
eligible/observed/unknown denominators. Retrieval failures score zero on labeled
answerable cases. Recall@k means at least one relevant hit per case, MRR uses the
first relevant rank and nDCG uses binary relevance with duplicate suppression.
For multi-search execution, ranking metrics use the **first successful retrieval**;
all ordered retrieval calls are retained separately and citations are the distinct
evidence union. Citation scope validity checks document membership only; it is not
claim support, citation precision or human faithfulness. Tool allowlists check names,
not schema validation or capability sufficiency. Unobserved validation, refusal,
token usage and cost remain null. Paired 95% bootstrap intervals average repetition
deltas per case before resampling cases and report missing pairs. They quantify
these structural metrics only.

Raw records exclude question/answer/document text, filenames, model reasoning,
tool arguments and exception strings. A hash replaces the answer, and safe citation
IDs/pages, tool names and error codes support diagnostics. See [report policy](reports/README.md).

Default pytest covers fake-provider regression/schema/scoring tests. CI also runs
the synthetic CLI and retains its sanitized offline artifact. Independent ≥100-case
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
