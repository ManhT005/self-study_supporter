"""Explicit test-only HTTP server; no fixture switch exists in production API."""

import os
from pathlib import Path

from apps.api.app.main import HTTPSettings, create_app
from apps.api.tests.fixtures import FixtureFactory


def create_test_app():
    root = Path(__file__).resolve().parents[1]
    directory = root / ".test-tmp"
    directory.mkdir(exist_ok=True)
    target = directory / "browser.db"
    return create_app(
        lambda: FixtureFactory(f"sqlite:///{target}"),
        HTTPSettings(os.getenv("WEB_ORIGIN", "http://127.0.0.1:3000"), False),
    )
