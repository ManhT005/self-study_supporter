# Frontend handoff contract (proposal for P1)

This is a design contract, not a running HTTP API. P0 exposes Python retrieval DTOs
and ports; no FastAPI server or Next.js client has been deployed. The accompanying
OpenAPI document gives the future client a bounded retrieval mock surface.

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
