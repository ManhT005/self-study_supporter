from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from study_supporter.domain.errors import DocumentUnsupported


def test_failed_ingestion_marks_failed_and_removes_tempfile(monkeypatch):
    from ui.components import sidebar

    state = SimpleNamespace(user_id="1")
    monkeypatch.setattr(sidebar.st, "session_state", state)
    monkeypatch.setattr(sidebar.st, "status", MagicMock())
    monkeypatch.setattr(sidebar.st, "progress", MagicMock())
    monkeypatch.setattr(sidebar, "create_document", lambda *args: (9, "documents_9"))
    updated, temporary = [], []
    monkeypatch.setattr(
        sidebar,
        "update_document_status",
        lambda *args, **kwargs: updated.append((args, kwargs)),
    )

    def fail_parse(path, **kwargs):
        temporary.append(Path(path))
        assert Path(path).exists()
        raise DocumentUnsupported("needs OCR")

    monkeypatch.setattr(sidebar, "parse_pdf", fail_parse)
    monkeypatch.setattr(sidebar, "_get_embedding_provider", MagicMock())
    with pytest.raises(DocumentUnsupported):
        sidebar._process_uploaded_file_with_progress(
            SimpleNamespace(name="blank.pdf", type="application/pdf"), b"%PDF-fixture"
        )
    assert not temporary[0].exists()
    assert updated == [((9,), {"status": "failed", "user_id": 1})]
    sidebar._get_embedding_provider.assert_not_called()
