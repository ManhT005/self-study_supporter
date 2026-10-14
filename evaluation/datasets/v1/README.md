# v1 contract smoke dataset

`smoke.jsonl` contains 15 synthetic development cases over three short text documents
and two fictional accounts: six factual, three synonym, two multi-hop, two missing
evidence and two cross-account scope probes. `fixtures/corpus.json` is public text,
not private PDFs. Rebuild byte-for-byte from the repository root:

```powershell
.venv/Scripts/python evaluation/datasets/v1/fixtures/build_dataset.py
```

The case source hash pins the exact corpus bytes. Labels, reference facts, allowed
tool names, source pages and account ownership are hand-written contract fixtures;
they have not undergone independent human annotation or consensus. All cases are
development-only. The loader rejects duplicate IDs, malformed labels, missing
personalized-history fixtures and documents appearing in multiple splits.
`.gitattributes` pins this fixture tree to LF so Git checkout on Windows and Linux
preserves the same bytes and source hashes.

Labels now distinguish required tools from allowed names. Non-scope smoke cases
require `search_docs` only for declared tool-capable variants; RAG-only is exempt.
Scope probes expect denial before any tool. Adding these labels changes the dataset
SHA-256 while preserving the corpus hash. Golden revision 1 pins this labeled dataset
and metric schema version 2; older reports retain their original metric semantics.

This is not the proposed 120-question benchmark and does not pass Phase 1's ≥100-case
acceptance gate. Before online signoff, provide approved PDFs/document hashes,
independent labels for all seven categories, explicit isolated history/quiz fixtures,
document-separated validation and frozen holdout, reviewer consensus and a paired
real-model report. Quiz validity, prompt-injection robustness and personalization
are not evaluated by this smoke. Keep private assets and generated reports in `data/`.
