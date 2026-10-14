import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.orchestration.legacy_react.adapter import LegacyReActAdapter


def test_concurrent_questions_on_same_adapter_do_not_share_evidence_or_tools():
    barrier = Barrier(2)

    class LLM:
        def chat(self, messages, **kwargs):
            text = messages[-1]["content"]
            question = text.split("Câu hỏi: ", 1)[1].split("\n", 1)[0]
            if "Observation:" in text:
                return ChatResponse(text="Final Answer: " + question)
            return ChatResponse(
                text="Action: search_docs\nAction Input: " + json.dumps({"query": question})
            )

    class Retriever:
        def execute(self, query):
            barrier.wait(timeout=10)
            return [Evidence(query.question, "doc-a", query.question, "a.pdf", 1, 1)]

    context = AppContext("A", ("doc-a",))
    tools_factory = Mock(return_value=[])
    adapter = LegacyReActAdapter(context, LLM(), Retriever(), tools_factory)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda question: adapter.execute(AnswerRequest(context, question)), ("one", "two")
            )
        )
    assert [(r.answer, r.evidences[0].chunk_id) for r in results] == [
        ("one", "one"),
        ("two", "two"),
    ]
    assert tools_factory.call_count == 2


def test_foreign_context_is_rejected_before_constructing_tools_or_calling_model():
    llm, retriever, tools_factory = Mock(), Mock(), Mock()
    adapter = LegacyReActAdapter(AppContext("A", ("doc-a",)), llm, retriever, tools_factory)
    with pytest.raises(EvidenceNotFound):
        adapter.execute(AnswerRequest(AppContext("B", ("doc-a",)), "question"))
    tools_factory.assert_not_called()
    retriever.execute.assert_not_called()
    llm.chat.assert_not_called()
