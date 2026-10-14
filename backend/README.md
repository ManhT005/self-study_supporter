# study-supporter

Python 3.11–3.12, src layout. Install with `python -m pip install -e ./backend`.
Core installs only deterministic NumPy/Pydantic/NetworkX dependencies. Runtime
drivers are in the runtime extra; Streamlit lives in apps/streamlit_legacy.
Contracts require authenticated identity; ownership is checked before retrieval.
Run `python scripts/check_import_boundaries.py` and `python -m pytest` from repo root.
