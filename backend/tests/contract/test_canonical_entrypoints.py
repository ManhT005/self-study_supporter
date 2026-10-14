"""All executable callers must use the installed distribution after shim removal."""

import ast
from pathlib import Path


def test_no_legacy_namespace_in_entrypoints_or_helpers():
    root = Path(__file__).resolve().parents[3]
    sources = [root / "main.py", root / "eval_test.py", root / "backend/migrations/env.py"]
    for directory in ["apps", "scripts", "evaluation", "backend/tests"]:
        sources.extend((root / directory).rglob("*.py"))
    for path in sources:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            imports = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert all(name.split(".")[0] not in {"src", "ui"} for name in imports), path
