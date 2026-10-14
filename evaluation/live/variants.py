"""Production use cases, hybrid retrieval and all four original ReAct tools."""

from dataclasses import replace

from evaluation.adapters.rag_only import RagOnlyAdapter
from study_supporter.application.contracts.agent import AgentUsage
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.use_cases.learning import SaveNoteUseCase, GetProgressUseCase
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.orchestration.legacy_react.adapter import LegacyReActAdapter
from study_supporter.orchestration.legacy_react.tools.generate_quiz import GenerateQuizTool
from study_supporter.orchestration.legacy_react.tools.save_note import SaveNoteTool
from study_supporter.orchestration.legacy_react.tools.get_progress import GetProgressTool


def validate_scope(factory, corpus, case):
    if case.source_hash != corpus.source_hash:
        raise ValueError("Unknown variant or frozen source mismatch")
    if case.user_fixture not in corpus.users:
        raise ValueError("Unknown authenticated fixture")
    context = AppContext(
        corpus.users[case.user_fixture],
        tuple(corpus.documents[d].document_id for d in case.document_ids),
    )
    documents = []
    for alias in case.document_ids:
        doc = corpus.documents[alias]
        # Real SQL ownership, before vectors or model calls; public domain behavior stays uniform.
        document = factory.documents.get(context, int(doc.document_id))
        if document["file_hash"] != doc.pdf_sha256 or document["status"] != "ready":
            raise ValueError("Document/index snapshot differs from labels")
        documents.append(document)
    return context, documents


def execute_variant(factory, corpus, case, variant, llm, top_k=3):
    if variant not in {"rag_only", "legacy_react"}:
        raise ValueError("Unknown variant")
    context, documents = validate_scope(factory, corpus, case)
    if case.requires_history:
        history = corpus.history_fixtures.get(case.history_fixture)
        if (
            not history
            or history.get("user_fixture") != case.user_fixture
            or history.get("chat_history")
        ):
            raise ValueError("Unsupported or foreign chat-history fixture")
        for attempt in history.get("progress", []):
            factory.progress_repository.record_attempt(
                context.user_id,
                attempt["topic"],
                attempt["question"],
                attempt["is_correct"],
                int(context.active_document_ids[0]),
            )
    retrieval = factory.retriever()

    def tools():
        from study_supporter.infrastructure.persistence.chroma.note_repository import LongTermMemory

        store = factory.vector_store(documents[0])
        notes = SaveNoteUseCase(
            LongTermMemory(
                store, lambda text: factory.embedding.embed([text], "RETRIEVAL_QUERY")[0]
            )
        )
        return [
            GenerateQuizTool(llm),
            SaveNoteTool(notes, context.user_id),
            GetProgressTool(GetProgressUseCase(factory.progress_repository), context.user_id),
        ]

    adapter = (
        RagOnlyAdapter(context, llm, retrieval, top_k)
        if variant == "rag_only"
        else LegacyReActAdapter(context, llm, retrieval, tools)
    )
    result = adapter.execute(AnswerRequest(context, case.question))
    reverse = {doc.document_id: alias for alias, doc in corpus.documents.items()}
    evidence = []
    for item in result.evidences:
        if item.document_id not in context.active_document_ids:
            raise EvidenceNotFound("Evidence outside authenticated documents")
        evidence.append(replace(item, document_id=reverse[item.document_id]))
    usage = None
    if llm.usage:
        counts = {
            key: sum(u[key] for u in llm.usage)
            if all(u and u.get(key) is not None for u in llm.usage)
            else None
            for key in ("input_tokens", "output_tokens")
        }
        usage = AgentUsage(**counts)
    return replace(result, evidences=tuple(evidence), usage=usage)
