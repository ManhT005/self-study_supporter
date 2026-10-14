# Annotation rubric v2.1

Assign each case two separate annotators. They submit labels without seeing the other
vote or any candidate model answer. Preserve disagreements; a third person resolves
them and records an explicit adjudicated label. Use opaque reviewer IDs in public
summaries; private annotation records retain provenance and review permissions.

For factual/synonym cases, list minimum answer facts and supporting chunks/pages;
for multi-hop, require at least two relevant chunks and cover every reference fact.
Quotes must be exact excerpts of frozen indexed text. Review that each quote supports
its claimed fact rather than merely sharing words. Unanswerable cases have no gold
supporting chunks/facts and require an explicit abstention judgment.

Quiz labels record count (1–15), topic concepts, four distinct options, one correct
answer and grounded explanations. Personalized labels reference an explicit isolated
progress/note/history fixture owned by the requesting account. Privacy cases identify
an expected scoped denial or owned injection source; they must not authorize model
identity arguments or cross-account writes. Judge failure, unknown usage and missing
support must never become a passing score.

Freeze chunks after production ingest/indexing; do not reuse synthetic chunk IDs.
Group source aliases, identical PDF/content versions and topics before assigning
70/15/15 splits. Inspect category coverage by split. Do not tune against holdout;
unlock only for final acceptance after configuration and reviewer approval. Keep
actual source text, gold facts and review packets in ignored private directories.
