from study_supporter.infrastructure.embeddings.sentences import embed_sentences
from study_supporter.infrastructure.embeddings.chunk_embeddings import embed_chunks


class EmbeddingPipeline:
    def __init__(self, provider):
        self.provider = provider
        self.dimension = provider.dimension

    def sentences(self, sentences, on_progress=None):
        return embed_sentences(sentences, self.provider, on_progress=on_progress)

    def chunks(self, chunks, on_progress=None):
        return embed_chunks(chunks, self.provider, on_progress=on_progress)
