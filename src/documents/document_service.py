from src.db.database import SessionLocal, Base, engine
from src.db.models import Document

Base.metadata.create_all(engine)


def create_document(user_id: int, filename: str) -> tuple[int, str]:
    """
    Tạo bản ghi document (status='processing'), trả về (document_id, collection_name).
    collection_name = f"documents_{document_id}" — mỗi tài liệu 1 collection ChromaDB
    RIÊNG BIỆT, không dùng chung/filter metadata, để tránh đụng chunk_id giữa các
    tài liệu khác nhau (chunk_id tính từ content hash, có thể trùng giữa 2 file).
    """
    session = SessionLocal()
    try:
        doc = Document(user_id=user_id, filename=filename, chroma_collection_name="", status="processing")
        session.add(doc)
        session.commit()
        session.refresh(doc)

        collection_name = f"documents_{doc.id}"
        doc.chroma_collection_name = collection_name
        session.commit()

        return doc.id, collection_name
    finally:
        session.close()


def update_document_status(
    document_id: int,
    status: str,
    page_count: int | None = None,
    chunk_count: int | None = None,
) -> None:
    session = SessionLocal()
    try:
        doc = session.query(Document).filter_by(id=document_id).first()
        if doc is None:
            return
        doc.status = status
        if page_count is not None:
            doc.page_count = page_count
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        session.commit()
    finally:
        session.close()


def update_document_graph(document_id: int, graph_json: dict | None) -> None:
    session = SessionLocal()
    try:
        doc = session.query(Document).filter_by(id=document_id).first()
        if doc is None:
            return
        doc.concept_graph_json = graph_json
        session.commit()
    finally:
        session.close()


def get_latest_ready_document(user_id: int) -> dict | None:
    """
    Trả về document 'ready' gần nhất của user, dạng dict (không trả ORM object
    sau khi đã đóng session, tránh lỗi detached instance nếu code gọi sau này
    lỡ truy cập thêm field chưa load).
    """
    session = SessionLocal()
    try:
        doc = (
            session.query(Document)
            .filter_by(user_id=user_id, status="ready")
            .order_by(Document.created_at.desc())
            .first()
        )
        if doc is None:
            return None
        return {
            "id": doc.id,
            "filename": doc.filename,
            "chroma_collection_name": doc.chroma_collection_name,
            "concept_graph_json": doc.concept_graph_json,
        }
    finally:
        session.close()