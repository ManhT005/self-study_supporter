import os
import fitz  # PyMuPDF
from src.rag.schemas import DocumentPage

def parse_pdf(file_path: str) -> list[DocumentPage]:
    """
    Đọc file PDF, trả về danh sách DocumentPage (1 phần tử/trang).
    """
    doc = fitz.open(file_path)
    pages = []

    # TODO: lặp qua từng trang trong `doc`
    #   - lấy text bằng page.get_text()
    #   - bỏ qua trang có text rỗng/toàn khoảng trắng (tránh trang bìa trắng, trang trắng giữa chương)
    #   - tạo DocumentPage với source = tên file (dùng os.path.basename), page_number bắt đầu từ 1
    #   - append vào `pages`

    source = os.path.basename(file_path)
    
    for i, page in enumerate(doc):
        text = page.get_text()

        if not text.strip():
            continue

        page_data = DocumentPage(
            source= source,
            page_number= i+1,
            text= text
        )

        pages.append(page_data)

    doc.close()
    return pages


# Bạn dùng text.strip() để check rỗng nhưng lưu text gốc (chưa strip) vào page_data 
# — điều này đúng ý đồ, vì giữ nguyên format gốc để chunker xử lý tốt hơn, không bị 
# mất xuống dòng/khoảng cách có ý nghĩa.


# Trường hợp file PDF là ảnh scan (không có text layer), get_text() sẽ luôn trả về rỗng cho 
# toàn bộ trang → hàm này sẽ trả về pages rỗng toàn bộ mà không báo lỗi gì. 
# Với DSA.pdf (thường là slide/text thuần) chắc không gặp, nhưng đáng để nhớ: nếu sau này
# gặp PDF scan, cần thêm OCR (không nằm trong scope sprint 1, ghi chú lại thôi).