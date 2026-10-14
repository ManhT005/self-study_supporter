from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.infrastructure.persistence.sqlalchemy.models import Document
from study_supporter.infrastructure.persistence.sqlalchemy import auth_repository


def document_data(doc):
    return {
        name: getattr(doc, name)
        for name in [
            "id",
            "filename",
            "chroma_collection_name",
            "status",
            "file_hash",
            "page_count",
            "chunk_count",
            "concept_graph_json",
        ]
    }


class UserRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    def register(self, username, password):
        return auth_repository.register_user(username, password, session_factory=self.sessions)

    def authenticate(self, username, password):
        return auth_repository.authenticate_user(username, password, session_factory=self.sessions)


class DocumentRepository:
    def __init__(self, sessions):
        self.sessions = sessions

    def create(self, user_id, filename, file_hash=None):
        with self.sessions.begin() as session:
            doc = Document(
                user_id=int(user_id),
                filename=filename,
                file_hash=file_hash,
                chroma_collection_name="",
                status="processing",
            )
            session.add(doc)
            session.flush()
            doc.chroma_collection_name = f"documents_{doc.id}"
            return document_data(doc)

    def list(self, user_id):
        with self.sessions() as session:
            return [
                document_data(doc)
                for doc in session.query(Document)
                .filter_by(user_id=int(user_id))
                .order_by(Document.created_at.desc(), Document.id.desc())
                .all()
            ]

    def recover_interrupted(self):
        with self.sessions.begin() as session:
            return (
                session.query(Document).filter_by(status="processing").update({"status": "failed"})
            )

    def get(self, user_id, document_id):
        with self.sessions() as session:
            doc = (
                session.query(Document).filter_by(id=int(document_id), user_id=int(user_id)).first()
            )
            if doc is None:
                raise EvidenceNotFound("Document not found")
            return document_data(doc)

    def latest(self, user_id):
        with self.sessions() as session:
            doc = (
                session.query(Document)
                .filter_by(user_id=int(user_id), status="ready")
                .order_by(Document.created_at.desc())
                .first()
            )
            return document_data(doc) if doc else None

    def find_hash(self, user_id, file_hash):
        with self.sessions() as session:
            doc = (
                session.query(Document)
                .filter_by(user_id=int(user_id), file_hash=file_hash)
                .order_by(Document.created_at.desc())
                .first()
            )
            return document_data(doc) if doc else None

    def owns(self, user_id, document_id):
        try:
            self.get(user_id, document_id)
            return True
        except (EvidenceNotFound, ValueError):
            return False

    def update(self, user_id, document_id, **values):
        allowed = {"status", "page_count", "chunk_count", "concept_graph_json", "file_hash"}
        if not values.keys() <= allowed:
            raise ValueError("Unsupported document fields")
        with self.sessions.begin() as session:
            doc = (
                session.query(Document).filter_by(id=int(document_id), user_id=int(user_id)).first()
            )
            if doc is None:
                raise EvidenceNotFound("Document not found")
            if "status" in values and values["status"] not in {"processing", "ready", "failed"}:
                raise ValueError("Invalid document status")
            if (
                values.get("status") == "ready"
                and (values.get("chunk_count", doc.chunk_count) or 0) < 1
            ):
                raise ValueError("READY requires indexed chunks")
            for key, value in values.items():
                setattr(doc, key, value)
