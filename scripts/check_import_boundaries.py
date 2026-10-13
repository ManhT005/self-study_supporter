"""AST architecture gate for the new src-layout package."""

import ast
import sys
from pathlib import Path

PURE = {"domain", "application", "ai"}
IO_DRIVERS = {"urllib", "http", "socket", "sqlite3", "subprocess"}
# Exact deterministic modules only; SDKs/network remain forbidden in every pure layer.
DETERMINISTIC_IMPORTS = {
    "study_supporter.domain.documents": {"pydantic"},
    "study_supporter.domain.knowledge_graph": {"pydantic"},
    "study_supporter.ai.ingestion.chunking": {"numpy"},
}
ALLOWED = {
    "domain": {"domain"},
    "ai": {"ai", "domain"},
    "application": PURE,
    "infrastructure": PURE | {"infrastructure", "config"},
    "orchestration": PURE | {"orchestration"},
    "interfaces": {"interfaces", "application", "domain"},
}
# Core is stdlib-only today. Allowing only stdlib catches new SDKs automatically.


def violations(source: str, module: str) -> list[str]:
    layer = module.split(".")[1] if "." in module else ""
    failures = []
    for node in ast.walk(ast.parse(source)):
        targets = []
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = module.split(".")[: -node.level]
                base = ".".join(parts + ([base] if base else []))
            targets = [base]
            if base == "study_supporter":
                targets.extend(f"{base}.{alias.name}" for alias in node.names)
        for target in targets:
            root = target.split(".")[0]
            if root in {"src", "ui"}:
                failures.append(f"{module}:{node.lineno}: legacy import {target}")
            elif root == "study_supporter" and layer in ALLOWED:
                target_layer = target.split(".")[1] if "." in target else ""
                if target_layer and target_layer not in ALLOWED[layer]:
                    failures.append(f"{module}:{node.lineno}: forbidden layer {target}")
            elif layer in PURE and (
                root in IO_DRIVERS
                or (
                    root not in sys.stdlib_module_names
                    and root != "study_supporter"
                    and root not in DETERMINISTIC_IMPORTS.get(module, set())
                )
            ):
                failures.append(f"{module}:{node.lineno}: forbidden core import {target}")
    return failures


def check(root: Path) -> list[str]:
    failures = []
    for path in root.rglob("*.py"):
        parts = path.relative_to(root.parent).with_suffix("").parts
        module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        # Package __init__ behaves as a module inside that package for relative imports.
        context = module + ".__init__" if path.name == "__init__.py" else module
        failures.extend(violations(path.read_text(encoding="utf-8"), context))
    return failures


if __name__ == "__main__":
    errors = check(Path(__file__).resolve().parents[1] / "backend/src/study_supporter")
    print("\n".join(errors) if errors else "Import boundaries passed")
    raise SystemExit(bool(errors))
