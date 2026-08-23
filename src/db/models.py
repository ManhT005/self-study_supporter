from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, nullable=True, index=True)  # sha256 nội dung file — để phát hiện upload trùng
    chroma_collection_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="processing")  # processing | ready | failed
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, nullable=True)
    concept_graph_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    # Nullable vì bảng đã tồn tại từ trước khi có document_id -> dữ liệu cũ vẫn hợp lệ.
    # LƯU Ý: nếu bảng quiz_attempts đã tồn tại sẵn trên Postgres (Supabase) từ lần
    # chạy trước, thêm cột này vào model KHÔNG tự động ALTER TABLE — cần chạy tay:
    #   ALTER TABLE quiz_attempts ADD COLUMN document_id INTEGER REFERENCES documents(id);
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    topic = Column(String, nullable=False)
    question = Column(String, nullable=False)
    is_correct = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)