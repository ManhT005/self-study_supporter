import ast
from pathlib import Path


def test_components_do_not_import_storage_provider_or_algorithm_implementations():
    root = Path(__file__).resolve().parents[3] / "apps/streamlit_legacy/components"
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for module in modules:
                assert not module.startswith(
                    (
                        "src",
                        "ui",
                        "study_supporter.infrastructure",
                        "study_supporter.orchestration",
                        "study_supporter.ai",
                    )
                ), (path, module)


def test_deterministic_allowlist_cannot_enable_network_imports():
    from scripts.check_import_boundaries import violations

    assert not violations("import numpy", "study_supporter.ai.ingestion.chunking")
    assert violations("import requests", "study_supporter.ai.ingestion.chunking")
    assert violations("import numpy", "study_supporter.domain.arbitrary")
