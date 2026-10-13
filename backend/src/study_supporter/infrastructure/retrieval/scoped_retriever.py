from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.domain.errors import EmbeddingUnavailable
from study_supporter.infrastructure.retrieval.bm25_adapter import BM25Index
from study_supporter.infrastructure.retrieval.hybrid_adapter import hybrid_search


class ScopedHybridRetriever:
    def __init__(self, documents, vectors, embeddings):
        self.documents, self.vectors, self.embeddings = documents, vectors, embeddings
        self._indexes = {}

    def retrieve(self, query):
        results = []
        for doc_id in query.document_ids:
            document = self.documents.get(query.user_id, int(doc_id))
            if document["status"] != "ready":
                continue
            key = (query.user_id, doc_id, document["chunk_count"])
            if key not in self._indexes:
                store = self.vectors(document)
                chunks = store.load_all_chunks()
                if not chunks:
                    continue
                self._indexes[key] = store, BM25Index(chunks)
            store, sparse = self._indexes[key]

            def embed(text):
                vector = self.embeddings.embed([text], "RETRIEVAL_QUERY")[0]
                if len(vector) != self.embeddings.dimension:
                    raise EmbeddingUnavailable("Embedding dimension mismatch")
                return vector

            chunks = hybrid_search(query.question, store, sparse, embed, query.top_k)
            results.extend(
                Evidence(
                    chunk.chunk_id,
                    doc_id,
                    chunk.text,
                    chunk.source,
                    chunk.page_start,
                    chunk.page_end,
                )
                for chunk in chunks
            )
        return results[: query.top_k]
