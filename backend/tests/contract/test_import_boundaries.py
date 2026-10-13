from pathlib import Path

import pytest

from scripts.check_import_boundaries import check, violations


def test_actual_package():
    assert check(Path(__file__).resolve().parents[2] / "src/study_supporter") == []


@pytest.mark.parametrize(
    "source",
    [
        "import sqlalchemy",
        "from streamlit import session_state",
        "def run():\n    import requests",
        "from ..infrastructure import vectors",
        "from study_supporter import bootstrap",
        "from src.rag import chunker",
        "import google.genai",
        "from .. import infrastructure",
    ],
)
def test_gate_rejects_forbidden_imports(source):
    assert violations(source, "study_supporter.domain.example")
