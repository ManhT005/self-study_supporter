# study-supporter

Python 3.11–3.12, src layout. Install with `python -m pip install -e ./backend`.
Core has no runtime dependencies. Legacy adapters forward to unchanged pure RRF.
Contracts require authenticated identity; ownership is checked before retrieval.
Run `python scripts/check_import_boundaries.py` and `python -m pytest` from repo root.
