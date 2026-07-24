# src/rag/schemas.py — thêm/sửa
from pydantic import BaseModel

class DocumentPage(BaseModel):
    source: str
    page_number: int
    text: str

class SentenceUnit(BaseModel):
    source: str          # <-- mới thêm
    text: str
    page_number: int
    embedding: list[float] | None = None

class Chunk(BaseModel):
    chunk_id: str
    source: str
    page_start: int
    page_end: int
    text: str
    sentence_count: int