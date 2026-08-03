from datetime import datetime

from src.db.database import Base, engine, SessionLocal
from src.db.models import QuizAttempt

# Đảm bảo bảng tồn tại (users + quiz_attempts) — idempotent, gọi nhiều lần vô hại
Base.metadata.create_all(engine)


class ProgressDB:
    """
    Giờ dùng chung engine/Base với hệ thống auth (src/db/database.py) —
    cùng 1 database Postgres thật (hoặc SQLite khi dev local), không còn
    tự tạo file SQLite riêng như trước.
    """

    def __init__(self):
        self.Session = SessionLocal

    def record_attempt(self, user_id: str, topic: str, question: str, is_correct: bool) -> None:
        session = self.Session()
        try:
            attempt = QuizAttempt(
                user_id=user_id,
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
                return {"total_attempts": 0, "correct": 0, "accuracy": None, "topics": []}

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