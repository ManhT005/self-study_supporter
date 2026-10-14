# Canonical package and application boundaries

Owner: repository maintainer. Base: origin/develop 5c9a16d.
Foundation CI ed199ce: quality run 38431172824 completed/success; baseline rerun:
91 tests passed on Windows/Python 3.12.7 (16.60 seconds).

All product implementations migrate into one study-supporter distribution. During
each slice legacy modules may forward to canonical implementations, never vice versa.
Streamlit is presentation; authenticated AppContext supplies ownership to every use
case and tool. ORM/Chroma/SDK objects stay inside infrastructure/composition.
All runtime callers now use canonical imports; the temporary src/ui aliases have
been removed after retaining and running the original tests in backend/tests.

Preserve SQL tables/Alembic revision p0_0001, string quiz user IDs, documents_<id>,
user_memory, BGE-M3/1024D, semantic chunk hashes, BM25 tokenization, RRF and ReAct.
Deterministic vendor imports require exact-module allowlists and negative gate tests.
No LangGraph/FastAPI/Next.js is added in consolidation.

ApplicationFactory owns explicit Database disposal and a lazy shared embedding
provider. Account-bound LearningSession/RetrieveEvidenceTool instances are created
per authenticated document session. Ingestion receives repository/parser/embedding
and vector adapters, emits correlated progress and verifies IDs before READY.
Deterministic vendor exceptions are exact modules: Pydantic schemas/JSON parsing,
NumPy chunking and NetworkX graph algorithms. No SDK or network exception exists.

Dependency declarations are centralized in backend/pyproject.toml, deployment/dev
locks in requirements and environment templates in config. Native and Docker env
files are local inputs; their existing secret values are preserved. Existing SQL
and Chroma data require no migration or reindex for this refactor.

Local slice branches form a reviewable dependency stack rooted at origin/develop;
each commit/branch checkpoint maps to one plan responsibility. No merge into develop
or remote publication is implied by local implementation. Submit/rebase the slices
in plan order after review rather than creating one combined refactor PR.
