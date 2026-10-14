from sqlalchemy.engine import make_url

from src.db.database import _get_database_url


def test_password_with_reserved_characters(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:/#?%word")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///ignored.db")
    url = _get_database_url()
    assert url.password == "p@ss:/#?%word"
    assert make_url(url.render_as_string(hide_password=False)).password == url.password
    assert "p@ss" not in str(url)
