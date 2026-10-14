import fitz
import pytest

from study_supporter.domain.upload_validation import validate_pdf_upload
from study_supporter.ai.ingestion.chunking import (
    compute_breakpoints,
    compute_distances,
    flatten_pages_to_sentences,
    group_sentences_into_chunks,
)
from study_supporter.infrastructure.documents.pymupdf_parser import parse_pdf
from study_supporter.domain.documents import DocumentPage
from study_supporter.domain.errors import DocumentUnsupported
from study_supporter.domain.errors import EmbeddingUnavailable


@pytest.mark.parametrize(
    "text,count",
    [("", 0), ("One sentence.", 1), ("First sentence. Second sentence.", 2)],
)
def test_small_documents(text, count):
    sentences = flatten_pages_to_sentences(
        [DocumentPage(source="fixture.pdf", page_number=2, text=text)]
    )
    assert len(sentences) == count
    for sentence in sentences:
        sentence.embedding = [1.0, 0.0]
    chunks = group_sentences_into_chunks(
        sentences, compute_breakpoints(sentences, compute_distances(sentences))
    )
    assert len(chunks) == bool(count)
    if chunks:
        assert chunks[0].source == "fixture.pdf"
        assert chunks[0].page_start == chunks[0].page_end == 2


def test_blank_pdf_and_corrupt_pdf(tmp_path):
    path = tmp_path / "blank.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.save(path)
    with pytest.raises(DocumentUnsupported, match="OCR"):
        parse_pdf(str(path))
    path.write_bytes(b"corrupt")
    with pytest.raises(DocumentUnsupported):
        parse_pdf(str(path))


def test_two_page_pdf_provenance(tmp_path):
    path = tmp_path / "fixture.pdf"
    with fitz.open() as doc:
        for number in [1, 2]:
            doc.new_page().insert_text((72, 72), f"Page {number}. Text sentence.")
        doc.save(path)
    result = parse_pdf(str(path))
    assert [page.page_number for page in result.pages] == [1, 2]
    assert all(page.source == "fixture.pdf" for page in result.pages)


@pytest.mark.parametrize(
    "name,mime,content",
    [
        ("x.txt", "text/plain", b"%PDF-"),
        ("x.pdf", "image/png", b"%PDF-"),
        ("x.pdf", "application/pdf", b""),
        ("x.pdf", None, b"bad"),
    ],
)
def test_invalid_upload(name, mime, content):
    with pytest.raises(DocumentUnsupported):
        validate_pdf_upload(name, mime, content)


def test_incomplete_embeddings_fail_closed():
    from unittest.mock import Mock
    from study_supporter.infrastructure.embeddings.sentences import embed_sentences

    sentences = flatten_pages_to_sentences(
        [DocumentPage(source="fixture.pdf", page_number=1, text="First sentence. Second sentence.")]
    )
    provider = Mock()
    provider.embed.return_value = [[1.0, 0.0]]
    with pytest.raises(EmbeddingUnavailable):
        embed_sentences(sentences, provider)
