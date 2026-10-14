"""Explicit annotation/provenance fields missing from the structural smoke schema."""

import hashlib
import json

from pydantic import Field, model_validator

from evaluation.schema import EvaluationCase, StrictModel


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


class ApprovedDocument(StrictModel):
    document_id: str
    user_fixture: str
    topic_group: str = Field(min_length=1)
    content_family: str = Field(min_length=1)
    pdf_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: int = Field(ge=1)
    permission_reference: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)


class IndexedChunk(StrictModel):
    document: str
    chunk_id: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    text: str = Field(min_length=1, repr=False)
    embedding_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class CorpusSnapshot(StrictModel):
    corpus_version: str = "v2"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dimension: int = 1024
    embedding_revision: str
    database_revision: str
    users: dict[str, str]
    documents: dict[str, ApprovedDocument]
    chunks: tuple[IndexedChunk, ...]
    history_fixtures: dict[str, dict] = Field(default_factory=dict)
    payload_hashes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_sources(self):
        if self.embedding_model != "BAAI/bge-m3" or self.embedding_dimension != 1024:
            raise ValueError("Existing BGE-M3 / 1024D contract required")
        if (
            len(set(self.users.values())) != len(self.users)
            or not self.documents
            or not self.chunks
        ):
            raise ValueError("Distinct fixture accounts and indexed documents required")
        if len({doc.document_id for doc in self.documents.values()}) != len(self.documents):
            raise ValueError("Document aliases must identify distinct indexed documents")
        seen = set()
        for alias, doc in self.documents.items():
            if doc.user_fixture not in self.users:
                raise ValueError("Unknown document owner fixture")
        for chunk in self.chunks:
            if chunk.document not in self.documents or chunk.page_start > chunk.page_end:
                raise ValueError("Invalid chunk provenance")
            if chunk.page_end > self.documents[chunk.document].page_count:
                raise ValueError("Chunk page outside approved source")
            key = (chunk.document, chunk.chunk_id)
            if key in seen:
                raise ValueError("Duplicate indexed chunk")
            seen.add(key)
        return self

    @property
    def source_hash(self):
        return "sha256:" + fingerprint(self.model_dump(mode="json"))

    @property
    def index_hash(self):
        return fingerprint(
            sorted(((c.document, c.chunk_id, c.embedding_sha256) for c in self.chunks))
        )


class GoldLabel(StrictModel):
    expected_doc_ids: tuple[str, ...]
    relevant_chunk_ids: tuple[str, ...]
    reference_facts: tuple[str, ...]
    must_abstain: bool
    allowed_tools: tuple[str, ...]
    required_tools: tuple[str, ...]
    expected_error: str | None = None


class Annotation(StrictModel):
    annotator: str = Field(min_length=1)
    independently_submitted: bool
    label: GoldLabel


class FactSupport(StrictModel):
    fact_index: int = Field(ge=0)
    document: str
    chunk_id: str
    quote: str = Field(min_length=1, repr=False)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)


class QuizRubric(StrictModel):
    num_questions: int = Field(ge=1, le=15)
    concepts: tuple[str, ...] = Field(min_length=1)


class BenchmarkCase(EvaluationCase):
    # Keep the smoke schema untouched; actual benchmark annotation has its own version.
    annotation_version: str = "v2"
    rubric_version: str = "v2.1"
    annotations: tuple[Annotation, ...] = Field(min_length=2, max_length=2)
    adjudicator: str | None = None
    adjudicated_label: GoldLabel | None = None
    fact_support: tuple[FactSupport, ...] = ()
    quiz_rubric: QuizRubric | None = None

    @property
    def gold_label(self):
        return GoldLabel(**{name: getattr(self, name) for name in GoldLabel.model_fields})

    @model_validator(mode="after")
    def validate_consensus(self):
        if self.annotation_version != "v2" or self.rubric_version != "v2.1":
            raise ValueError("Unsupported annotation or rubric version")
        votes = self.annotations
        if len({vote.annotator for vote in votes}) != 2 or not all(
            v.independently_submitted for v in votes
        ):
            raise ValueError("Two distinct independent annotations required")
        if votes[0].label == votes[1].label:
            if self.gold_label != votes[0].label:
                raise ValueError("Consensus differs from benchmark gold")
        elif (
            not self.adjudicator
            or self.adjudicator in {v.annotator for v in votes}
            or self.adjudicated_label != self.gold_label
        ):
            raise ValueError("Disagreement requires independent adjudication")
        if self.must_abstain and (self.reference_facts or self.fact_support):
            raise ValueError("Unanswerable case cannot invent supported facts")
        if self.category in {"factual", "multi_hop", "synonyms"} and not self.reference_facts:
            raise ValueError("Answerable case requires reference facts")
        if self.category == "multi_hop" and len(set(self.relevant_chunk_ids)) < 2:
            raise ValueError("Multi-hop requires at least two relevant chunks")
        if self.category == "quiz" and self.quiz_rubric is None:
            raise ValueError("Quiz requires an explicit structural/topic rubric")
        if self.category == "personalized" and not self.requires_history:
            raise ValueError("Personalized cases require an explicit history/progress fixture")
        return self
