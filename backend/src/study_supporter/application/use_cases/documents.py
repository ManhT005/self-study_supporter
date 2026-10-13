from study_supporter.application.contracts.context import AppContext
from study_supporter.application.ports.learning import DocumentRepositoryPort


class OwnedDocuments:
    def __init__(self, repository: DocumentRepositoryPort):
        self.repository = repository

    def latest(self, context: AppContext):
        return self.repository.latest(context.user_id)

    def get(self, context: AppContext, document_id: int):
        return self.repository.get(context.user_id, document_id)

    def update(self, context: AppContext, document_id: int, **values):
        self.repository.update(context.user_id, document_id, **values)
