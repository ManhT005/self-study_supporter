"""Versioned, strict benchmark inputs and sanitized observation records."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal[
    "factual", "multi_hop", "synonyms", "unanswerable", "quiz", "personalized", "privacy"
]
ErrorCode = Literal[
    "NO_EVIDENCE",
    "INVALID_TOOL",
    "INVALID_SCHEMA",
    "TIMEOUT",
    "AUTH_SCOPE",
    "PROVIDER_ERROR",
    "RETRIEVAL_EMPTY",
    "QUIZ_INVALID",
    "INTERNAL",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class EvaluationCase(StrictModel):
    case_id: str = Field(min_length=1)
    category: Category
    question: str = Field(min_length=1)
    user_fixture: str = Field(min_length=1)
    document_ids: tuple[str, ...] = Field(min_length=1)
    expected_doc_ids: tuple[str, ...]
    relevant_chunk_ids: tuple[str, ...] = ()
    reference_facts: tuple[str, ...] = ()
    must_abstain: bool = False
    allowed_tools: tuple[str, ...] = ()
    requires_history: bool = False
    history_fixture: str | None = None
    expected_error: ErrorCode | None = None
    source_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    annotation_version: Literal["v1"] = "v1"
    labeler: str = Field(min_length=1)
    split: Literal["development", "validation", "holdout"] = "development"

    @model_validator(mode="after")
    def check_labels(self):
        if not self.question.strip() or any(not value.strip() for value in self.document_ids):
            raise ValueError("Question and document scope cannot be blank")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("Duplicate documents")
        if self.requires_history and not self.history_fixture:
            raise ValueError("Personalized cases require an explicit isolated history fixture")
        if self.must_abstain and self.relevant_chunk_ids:
            raise ValueError("Unanswerable cases cannot label supporting chunks")
        if not set(self.expected_doc_ids).issubset(self.document_ids):
            raise ValueError("Expected documents must be inside the requested scope")
        return self


class RunManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    git_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    git_dirty: bool
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_hash: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    execution_mode: Literal["offline", "online"]
    provider: str
    model_id: str
    prompt_hashes: dict[str, str] = Field(min_length=1)
    embedding_id: str
    index_hash: str
    top_k: int = Field(ge=1)
    seed: int
    temperature: float | None = None
    python_version: str
    platform: str
    database_revision: str | None = None
    chroma_collections: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_prompt_hashes(self):
        for name, digest in self.prompt_hashes.items():
            if not name or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Prompt digests must be SHA-256 hashes")
        return self


class CitationRecord(StrictModel):
    document_id: str
    chunk_id: str
    page_start: int | None
    page_end: int | None


class RetrievalRecord(StrictModel):
    query_sha256: str
    top_k: int = Field(ge=1)
    chunk_ids: tuple[str, ...]


class EvaluationRecord(StrictModel):
    run_id: str
    case_id: str
    category: Category
    variant: str
    repetition: int
    status: Literal["completed", "incomplete", "error"]
    elapsed_ms: float = Field(ge=0)
    trace_id: str | None = None
    answer_sha256: str | None = None
    retrieved_chunk_ids: tuple[str, ...] = ()
    citations: tuple[CitationRecord, ...] = ()
    retrieval_calls: tuple[RetrievalRecord, ...] = ()
    steps: int = 0
    tools_used: tuple[str, ...] = ()
    usage: dict[str, int | float | None] | None = None
    error_code: ErrorCode | None = None
    scores: dict[str, float | None] = Field(default_factory=dict)


def dataset_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_dataset(path: str | Path) -> tuple[EvaluationCase, ...]:
    cases = tuple(
        EvaluationCase.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if not cases or len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Dataset must contain unique case IDs and cannot be empty")
    # Freeze split membership by document, including multi-document cases.
    splits = {}
    for case in cases:
        for document in case.document_ids:
            if document in splits and splits[document] != case.split:
                raise ValueError("Document leakage between dataset splits")
            splits[document] = case.split
    return cases
