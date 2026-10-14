import pytest

from study_supporter.config import Settings


def test_secrets_not_in_repr_and_reserved_password_preserved():
    settings = Settings.from_mapping(
        {"POSTGRES_HOST": "db", "POSTGRES_PASSWORD": "s@cr:/et", "GEMINI_API_KEY": "private-key"}
    )
    assert settings.postgres_password == "s@cr:/et"
    assert "private-key" not in repr(settings) and "s@cr" not in repr(settings)


@pytest.mark.parametrize(
    "values",
    [
        {"POSTGRES_HOST": "db"},
        {"POSTGRES_PORT": "0"},
        {"OLLAMA_BASE_URL": "ftp://invalid"},
        {"EMBEDDING_DIMENSION": "768"},
    ],
)
def test_invalid_configuration(values):
    with pytest.raises(ValueError):
        Settings.from_mapping(values)
