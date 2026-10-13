"""Compatibility entrypoint; canonical presentation lives in apps/streamlit_legacy."""

import runpy

runpy.run_module("apps.streamlit_legacy.main", run_name="__main__")
