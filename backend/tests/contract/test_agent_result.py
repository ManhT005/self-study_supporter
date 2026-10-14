import json
from dataclasses import FrozenInstanceError, asdict
from unittest.mock import Mock

import pytest

from study_supporter.application.contracts.agent import AgentStatus
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.orchestration.legacy_react.adapter import LegacyReActAdapter


def test_legacy_result_is_safe_and_preserves_iteration_limit():
    llm, retriever = Mock(), Mock()
    llm.chat.return_value = ChatResponse(text="Action: secret-model-output\nAction Input: {}")
    context = AppContext("A", ("doc-a",))
    result = LegacyReActAdapter(context, llm, retriever, lambda: []).execute(
        AnswerRequest(context, "question")
    )
    assert result.status == AgentStatus.INCOMPLETE and result.steps == 5
    assert len(result.tool_calls) == 5
    assert all(call.validation == "not_observed" for call in result.tool_calls)
    assert all(call.name == "unknown_tool" for call in result.tool_calls)
    assert result.usage is None and result.abstained is None
    safe = json.dumps(asdict(result))
    assert "scratchpad" not in safe and "thought" not in safe and "tool_args" not in safe
    # The legacy fallback answer may echo observations, but telemetry exposes no unknown names.
    assert "secret-model-output" not in json.dumps([asdict(c) for c in result.tool_calls])
    with pytest.raises(FrozenInstanceError):
        result.answer = "mutation"


def test_all_search_evidence_is_retained_without_changing_legacy_tool_loop():
    context = AppContext("A", ("doc-a",))
    llm, retriever = Mock(), Mock()
    first = Evidence("one", "doc-a", "one", "a.pdf", 1, 1)
    second = Evidence("two", "doc-a", "two", "a.pdf", 2, 2)
    retriever.execute.side_effect = [[first], [first, second]]
    llm.chat.side_effect = [
        ChatResponse(text='Thought: private\nAction: search_docs\nAction Input: {"query":"one"}'),
        ChatResponse(text='Action: search_docs\nAction Input: {"query":"two"}'),
        ChatResponse(text="Final Answer: complete"),
        ChatResponse(text="Final Answer: no search"),
    ]
    adapter = LegacyReActAdapter(context, llm, retriever, lambda: [])
    first_result = adapter.execute(AnswerRequest(context, "question"))
    second_result = adapter.execute(AnswerRequest(context, "next"))
    assert first_result.answer == "complete" and first_result.evidences == (first, second)
    assert first_result.steps == 3 and first_result.status == AgentStatus.COMPLETED
    assert [call.chunk_ids for call in first_result.retrieval_calls] == [("one",), ("one", "two")]
    assert second_result.evidences == () and first_result.trace_id != second_result.trace_id
    assert "private" not in json.dumps(asdict(first_result))
