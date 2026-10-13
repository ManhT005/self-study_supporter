import importlib
import sys

sys.modules[__name__] = importlib.import_module(
    "study_supporter.infrastructure.retrieval.legacy_tools"
)
