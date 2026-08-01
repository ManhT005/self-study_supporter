import os
from dataclasses import dataclass
from typing import Callable

import fitz  # PyMuPDF
from src.rag.schemas import DocumentPage


@dataclass
class ParseResult:
    """Kết quả parse PDF — bao gồm cả metadata cho UI progress."""
    pages: list[DocumentPage]
    total_pages: int        # tổng số trang trong file (kể cả trang trắng)
    skipped_pages: int      # số trang bị bỏ qua (trắng)


def parse_pdf(
    file_path: str,
    on_progress: Callable[[int, int], None] | None = None,
) -> ParseResult:
    """
    Đọc file PDF, trả về ParseResult chứa danh sách DocumentPage
    (1 phần tử/trang có nội dung) cùng metadata.

    on_progress(current_page, total_pages): callback cập nhật UI.
    """
    doc = fitz.open(file_path)
    total_pages = len(doc)
    pages = []
    skipped = 0

    source = os.path.basename(file_path)

    for i, page in enumerate(doc):
        text = page.get_text()

        if on_progress:
            on_progress(i + 1, total_pages)

        if not text.strip():
            skipped += 1
            continue

        page_data = DocumentPage(
            source=source,
            page_number=i + 1,
            text=text,
        )
        pages.append(page_data)

    doc.close()
    return ParseResult(pages=pages, total_pages=total_pages, skipped_pages=skipped)


# Bạn dùng text.strip() để check rỗng nhưng lưu text gốc (chưa strip) vào page_data 
# — điều này đúng ý đồ, vì giữ nguyên format gốc để chunker xử lý tốt hơn, không bị 
# mất xuống dòng/khoảng cách có ý nghĩa.


# Trường hợp file PDF là ảnh scan (không có text layer), get_text() sẽ luôn trả về rỗng cho 
# toàn bộ trang → hàm này sẽ trả về pages rỗng toàn bộ mà không báo lỗi gì. 
# Với DSA.pdf (thường là slide/text thuần) chắc không gặp, nhưng đáng để nhớ: nếu sau này
# gặp PDF scan, cần thêm OCR (không nằm trong scope sprint 1, ghi chú lại thôi).