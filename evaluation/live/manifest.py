"""Reproducibility metadata without credentials, source text or provider fallback."""

import hashlib
import importlib.metadata
import platform
from pathlib import Path

from evaluation.rag_only import RAG_ONLY_PROMPT_TEMPLATE
from evaluation.schema import RunManifest, dataset_hash


def production_prompt_hash():
    from study_supporter.application.contracts.context import AppContext
    from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
    from study_supporter.orchestration.legacy_react.tools.retrieve_evidence import (
        RetrieveEvidenceTool,
    )
    from study_supporter.orchestration.legacy_react.tools.generate_quiz import GenerateQuizTool
    from study_supporter.orchestration.legacy_react.tools.save_note import SaveNoteTool
    from study_supporter.orchestration.legacy_react.tools.get_progress import GetProgressTool

    prompt = ReActOrchestrator(
        None,
        [
            RetrieveEvidenceTool(None, AppContext("fixture", ("fixture",))),
            GenerateQuizTool(None),
            SaveNoteTool(None, "fixture"),
            GetProgressTool(None, "fixture"),
        ],
    ).system_prompt
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def source_code_hash():
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    for directory in ("backend/src", "evaluation"):
        for path in sorted((root / directory).rglob("*.py")):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))
    return digest.hexdigest()


def manifest_for(corpus, dataset, *, git_sha, git_dirty, model, top_k=3, seed=42):
    return RunManifest(
        git_sha=git_sha,
        git_dirty=git_dirty,
        dataset_sha256=dataset_hash(dataset),
        source_hash=corpus.source_hash,
        execution_mode="online",
        provider="gemini",
        model_id=model,
        prompt_hashes={
            "rag_only": hashlib.sha256(RAG_ONLY_PROMPT_TEMPLATE.encode("utf-8")).hexdigest(),
            "legacy_react": production_prompt_hash(),
        },
        tool_capabilities={"rag_only": False, "legacy_react": True},
        embedding_id=corpus.embedding_model + "@" + corpus.embedding_revision,
        index_hash=corpus.index_hash,
        top_k=top_k,
        seed=seed,
        temperature=0.0,
        python_version=platform.python_version(),
        platform=platform.platform(),
        database_revision=corpus.database_revision,
        chroma_collections=tuple("documents_" + d.document_id for d in corpus.documents.values()),
    )


def environment_metadata():
    root = Path(__file__).resolve().parents[2]
    locks = {
        path: hashlib.sha256((root / path).read_bytes()).hexdigest()
        for path in ("requirements/runtime.txt", "requirements/dev.txt", "backend/pyproject.toml")
    }
    versions = {}
    for name in ("google-genai", "chromadb", "sentence-transformers", "torch", "rank-bm25"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "code_sha256": source_code_hash(),
        "lock_hashes": locks,
        "packages": versions,
        "cpu": platform.processor() or None,
        "embedding_dimension": 1024,
        "rrf_k": 60,
        "cache_policy": "embedding_warmed_per_sample/provider_cache_uncontrolled",
        "model_revision_policy": "observed_response_version_or_unknown",
        "hardware_note": "CPU/container metadata; GPU/RAM supplied by deployment evidence when relevant",
    }
