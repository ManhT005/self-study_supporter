"""Snapshot runtime HTTP OpenAPI; --check verifies the committed contract."""

import json
import sys
from pathlib import Path

from apps.api.app.main import create_app

target = Path(__file__).resolve().parents[1] / "docs/api/runtime-openapi.json"
content = json.dumps(create_app().openapi(), ensure_ascii=False, indent=2) + "\n"
if "--check" in sys.argv:
    if not target.exists() or target.read_text(encoding="utf-8") != content:
        raise SystemExit("HTTP contract drift: run python -m scripts.export_http_contract")
    print("HTTP OpenAPI snapshot matches runtime")
else:
    target.write_text(content, encoding="utf-8")
    print(f"Exported {target.name}")
