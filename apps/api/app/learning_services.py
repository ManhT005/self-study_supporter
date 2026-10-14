"""HTTP application composition and admission, independent of route DTOs."""

from threading import BoundedSemaphore

from starlette.exceptions import HTTPException

from study_supporter.domain.errors import EvidenceNotFound


class LearningServices:
    def __init__(self, factory):
        self.factory = factory
        self._ai_slots = BoundedSemaphore(2)

    def open(self, context, document_id, mode="auto"):
        document = self.factory.documents.get(context, document_id)
        if document["status"] != "ready":
            raise HTTPException(
                409, "Tài liệu chưa sẵn sàng để học. Kiểm tra trạng thái trong thư viện."
            )
        session = self.factory.open_document(context, document_id, mode)
        if session is None:
            raise EvidenceNotFound("Document content unavailable")
        return session

    def call_ai(self, callback):
        if not self._ai_slots.acquire(blocking=False):
            raise HTTPException(429, "AI đang bận. Vui lòng thử lại sau.")
        try:
            return callback()
        finally:
            self._ai_slots.release()
