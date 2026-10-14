import secrets
import time
from dataclasses import dataclass, field
from threading import Lock

from starlette.exceptions import HTTPException


@dataclass
class QuizEntry:
    owner: str
    document_id: int
    questions: list
    expires: float
    grades: dict = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)


class Quizzes:
    def __init__(self, capacity=1000, ttl=3600, clock=time.monotonic):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self.entries, self.lock = {}, Lock()

    def create(self, owner, document_id, questions):
        with self.lock:
            self.entries = {k: v for k, v in self.entries.items() if v.expires > self.clock()}
            if len(self.entries) >= self.capacity:
                raise OverflowError("Quiz capacity reached")
            key = secrets.token_urlsafe(24)
            self.entries[key] = QuizEntry(owner, document_id, questions, self.clock() + self.ttl)
            return key

    def get(self, key, owner, document_id):
        with self.lock:
            entry = self.entries.get(key)
            if (
                not entry
                or entry.owner != owner
                or entry.document_id != document_id
                or entry.expires <= self.clock()
            ):
                raise HTTPException(404, "Bài luyện tập đã hết hạn. Vui lòng tạo bài mới.")
            return entry
