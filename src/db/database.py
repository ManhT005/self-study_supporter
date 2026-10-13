import os
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base


def _get_database_url() -> str | URL:
    """
    Ưu tiên DATABASE_URL từ môi trường (Postgres thật, ví dụ Supabase).
    Fallback về SQLite local nếu chưa cấu hình — để dev vẫn chạy được
    không cần setup Postgres ngay từ đầu.
    """
    if os.getenv("POSTGRES_HOST"):
        return URL.create(
            "postgresql+psycopg2",
            username=os.getenv("POSTGRES_USER", "study"),
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["POSTGRES_HOST"],
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "study_supporter"),
        )
    return os.getenv("DATABASE_URL", "sqlite:///data/app.db")


def _get_connect_args(db_url: str | URL) -> dict:
    if str(db_url).startswith("sqlite"):
        # Streamlit có thể chạy đa luồng -> cần tắt check_same_thread cho SQLite
        return {"check_same_thread": False}
    return {}


DATABASE_URL = _get_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args=_get_connect_args(DATABASE_URL),
    pool_pre_ping=True,  # quan trọng với Postgres cloud (Supabase) — tự kiểm tra
    # kết nối còn sống trước khi dùng, tránh lỗi "connection closed"
    # khi app không hoạt động một thời gian rồi có request mới.
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
