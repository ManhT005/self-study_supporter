import importlib
import sys
sys.modules[__name__] = importlib.import_module("apps.streamlit_legacy.router")
