# src/memory/progress_db.py
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    topic = Column(String, nullable=False)
    question = Column(String, nullable=False)
    is_correct = Column(Integer, nullable=False)  # 0/1, SQLite không có bool riêng
    timestamp = Column(DateTime, default=datetime.utcnow)


class ProgressDB:
    def __init__(self, db_path: str = "data/progress.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

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