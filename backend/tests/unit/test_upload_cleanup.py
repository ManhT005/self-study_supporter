from pathlib import Path

import pytest

from study_supporter.domain.errors import DocumentUnsupported
from study_supporter.infrastructure.documents import pymupdf_parser


def test_failed_ingestion_removes_tempfile(monkeypatch):
    staged = []

    def fail_parse(path, **kwargs):
        staged.append(Path(path))
        assert Path(path).exists()
        raise DocumentUnsupported("needs OCR")

    monkeypatch.setattr(pymupdf_parser, "parse_pdf", fail_parse)
    with pytest.raises(DocumentUnsupported):
        pymupdf_parser.PdfParser().parse("blank.pdf", b"%PDF-fixture")
    assert not staged[0].exists()
    assert not staged[0].parent.exists()
