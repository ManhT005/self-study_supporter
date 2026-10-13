# Engineering foundation

Self Study Supporter remains a modular monolith with the existing Streamlit entrypoint.
Phase 0 extracts one pure retrieval slice into the `study-supporter` distribution,
then adds correctness tests, explicit database migrations and offline quality gates.
Next.js, FastAPI, LangGraph and new retrieval algorithms belong to later phases.

Composition remains in the legacy sidebar until application contracts are established.
PostgreSQL owns user/document/quiz records; persistent Chroma stores vectors and notes.
Both stores must be backed up at the same quiescent application boundary.

See [baseline](current-state.md), [boundaries](module-boundaries.md),
[decisions](adr/README.md) and [Phase 0 plan](../plans/PHASE_0_ENGINEERING_FOUNDATION.md).
