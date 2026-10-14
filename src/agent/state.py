"""Temporary compatibility alias; canonical implementation is installed."""
import importlib
import sys
sys.modules[__name__] = importlib.import_module("study_supporter.orchestration.legacy_react.state")
