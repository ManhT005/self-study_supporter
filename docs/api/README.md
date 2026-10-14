# Frontend handoff contract (proposal for P1)

The running FastAPI adapter now lives in `apps/api/app/main.py`. Its runtime
OpenAPI snapshot is `runtime-openapi.json`, used to generate frontend API types.
See [workspace operations](../operations/learning-workspace.md) for startup and
limits. `openapi.yaml` and the text below remain historical retrieval proposals;
they are not the current HTTP contract.

- Identity comes from the authenticated session/token; no request body `user_id`.
- Retrieve accepts document IDs, question and positive top_k. Server resolves each
  document against the authenticated owner before hitting retriever infrastructure.
- Unknown/foreign document: 404 without confirming another user's document exists.
- Evidence includes document_id, chunk_id, text, source, page bounds and optional score.
- Model/provider failure: 503; exhausted quota: 429; invalid input: 422.
- Sources in UI derive from returned evidence, not generic PDF/graph/progress labels.

`mock-retrieval.json` is a synthetic successful response usable before an API exists.
Chat streaming, quiz attempt idempotency, auth transport and long-running ingestion
endpoints need separate P1 decisions; do not infer them from the legacy Streamlit UI.
