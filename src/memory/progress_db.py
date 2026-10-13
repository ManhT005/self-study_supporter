from src.db.database import SessionLocal
from src.db.models import QuizAttempt, Document, User
from study_supporter.domain.errors import EvidenceNotFound


class ProgressDB:
    """
    Giờ dùng chung engine/Base với hệ thống auth (src/db/database.py) —
    cùng 1 database Postgres thật (hoặc SQLite khi dev local), không còn
    tự tạo file SQLite riêng như trước.
    """

    def __init__(self):
        self.Session = SessionLocal

    def record_attempt(
        self,
        user_id: str,
        topic: str,
        question: str,
        is_correct: bool,
        document_id: int | None = None,
    ) -> None:
        session = self.Session()
        try:
            if not session.query(User).filter_by(id=int(user_id)).first():
                raise EvidenceNotFound("User not found")
            if (
                document_id is not None
                and not session.query(Document)
                .filter_by(id=document_id, user_id=int(user_id))
                .first()
            ):
                raise EvidenceNotFound("Document not found")
            if type(is_correct) is not bool:
                raise ValueError("is_correct must be validated before recording")
            attempt = QuizAttempt(
                user_id=user_id,
                document_id=document_id,
                topic=topic,
                question=question,
                is_correct=int(is_correct),
            )
            session.add(attempt)
            session.commit()
        finally:
            session.close()

    def get_summary(self, user_id: str) -> dict:
        session = self.Session()
        try:
            attempts = session.query(QuizAttempt).filter_by(user_id=user_id).all()
            if not attempts:
                return {
                    "total_attempts": 0,
                    "correct": 0,
                    "accuracy": None,
                    "topics": [],
                }

            total = len(attempts)
            correct = sum(a.is_correct for a in attempts)
            topics = sorted(set(a.topic for a in attempts))

            return {
                "total_attempts": total,
                "correct": correct,
                "accuracy": round(correct / total * 100, 1),
                "topics": topics,
            }
        finally:
            session.close()
