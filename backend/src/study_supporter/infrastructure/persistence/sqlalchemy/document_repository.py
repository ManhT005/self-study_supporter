"""Compatibility functions delegate to the single repository implementation."""

from study_supporter.infrastructure.persistence.sqlalchemy.database import SessionLocal
from study_supporter.infrastructure.persistence.sqlalchemy.repositories import DocumentRepository


def create_document(user_id: int, filename: str, *, session_factory=None):
    doc = DocumentRepository(session_factory or SessionLocal).create(str(user_id), filename)
    return doc["id"], doc["chroma_collection_name"]


def update_document_status(
    document_id, status, page_count=None, chunk_count=None, *, user_id, session_factory=None
):
    values = {"status": status}
    if page_count is not None:
        values["page_count"] = page_count
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    DocumentRepository(session_factory or SessionLocal).update(str(user_id), document_id, **values)


def update_document_graph(document_id, graph_json, *, user_id, session_factory=None):
    DocumentRepository(session_factory or SessionLocal).update(
        str(user_id), document_id, concept_graph_json=graph_json
    )


def get_latest_ready_document(user_id, *, session_factory=None):
    return DocumentRepository(session_factory or SessionLocal).latest(str(user_id))
