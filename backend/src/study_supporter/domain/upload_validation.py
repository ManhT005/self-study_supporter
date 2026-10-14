from study_supporter.domain.errors import DocumentUnsupported

MAX_PDF_BYTES = 20 * 1024 * 1024


def validate_pdf_upload(filename: str, mime: str | None, content: bytes) -> None:
    if not filename.lower().endswith(".pdf") or mime not in {
        None,
        "application/pdf",
        "application/octet-stream",
    }:
        raise DocumentUnsupported("Chỉ hỗ trợ tài liệu PDF.")
    if not content or len(content) > MAX_PDF_BYTES:
        raise DocumentUnsupported("PDF phải có dữ liệu và không vượt quá 20 MB.")
    if not content.startswith(b"%PDF-"):
        raise DocumentUnsupported("Tệp không có định dạng PDF hợp lệ.")
