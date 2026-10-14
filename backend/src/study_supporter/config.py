from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default="sqlite:///data/app.db", repr=False)
    postgres_host: str | None = None
    postgres_port: int = 5432
    postgres_user: str = "study"
    postgres_db: str = "study_supporter"
    postgres_password: str = field(default="", repr=False)
    ollama_base_url: str = "http://localhost:11434"
    chroma_path: str = "data/chroma_db"
    chroma_host: str | None = None
    chroma_port: int = 8000
    gemini_api_key: str = field(default="", repr=False)
    groq_api_key: str = field(default="", repr=False)
    cerebras_api_key: str = field(default="", repr=False)
    github_token: str = field(default="", repr=False)
    openrouter_api_key: str = field(default="", repr=False)
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    ollama_model: str = "qwen2.5:1.5b"

    def __post_init__(self):
        if self.postgres_host and not self.postgres_password:
            raise ValueError("POSTGRES_PASSWORD is required with POSTGRES_HOST")
        if not 1 <= self.postgres_port <= 65535 or not 1 <= self.chroma_port <= 65535:
            raise ValueError("Invalid database port")
        if not self.ollama_base_url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must be an HTTP URL")
        if self.embedding_model != "BAAI/bge-m3" or self.embedding_dimension != 1024:
            raise ValueError("Existing vectors require BGE-M3 / 1024D")

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]):
        fields = {
            name: values[name.upper()]
            for name in cls.__dataclass_fields__
            if name.upper() in values and values[name.upper()] != ""
        }
        aliases = {"CHROMA_SERVER_HOST": "chroma_host", "CHROMA_SERVER_PORT": "chroma_port"}
        for key, name in aliases.items():
            if values.get(key):
                fields[name] = values[key]
        for key in ["postgres_port", "chroma_port", "embedding_dimension"]:
            if key in fields:
                fields[key] = int(fields[key])
        return cls(**fields)
