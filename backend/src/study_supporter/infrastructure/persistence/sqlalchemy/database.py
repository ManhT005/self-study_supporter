import os
from functools import lru_cache
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


Base = declarative_base()


class Database:
    def __init__(self, settings):
        url = settings.database_url
        if settings.postgres_host:
            url = URL.create(
                "postgresql+psycopg2",
                username=settings.postgres_user,
                password=settings.postgres_password,
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
            )
        self.engine = create_engine(url, connect_args=_get_connect_args(url), pool_pre_ping=True)
        self.sessions = sessionmaker(bind=self.engine)

    def close(self):
        self.engine.dispose()


@lru_cache(maxsize=1)
def default_database():
    """Compatibility CLI factory, lazy; primary application injects its Database."""
    from study_supporter.config import Settings

    return Database(Settings.from_mapping(os.environ))


def SessionLocal():
    return default_database().sessions()


def __getattr__(name):
    if name == "engine":
        return default_database().engine
    if name == "DATABASE_URL":
        return _get_database_url()
    raise AttributeError(name)
