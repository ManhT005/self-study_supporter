import asyncio
import json
from dataclasses import asdict
from unittest.mock import Mock

import pytest

pytest.importorskip("langchain")

from langchain_core.messages import AIMessage

from scripts.langchain_fixtures import ScriptedNativeModel, native_call
from study_supporter.application.contracts.agent import AgentStatus
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.domain.errors import EvidenceNotFound, QuotaExceeded
from study_supporter.domain.provider_errors import ProviderAuthenticationError, ProviderUnavailable
from study_supporter.orchestration.langchain_agent.adapter import LangChainAgentAdapter
from study_supporter.orchestration.langchain_agent.policy import ExecutionPolicy

CONTEXT = AppContext("A", ("doc-a",))
EVIDENCE = Evidence("chunk-a", "doc-a", "Study material", "a.pdf", 1, 1)


def make_adapter(responses, *, context=CONTEXT, retriever=None, **kwargs):
    model = ScriptedNativeModel(responses=responses)
    progress = Mock()
    progress.execute.return_value = {
        "total_attempts": 0,
        "correct": 0,
        "accuracy": None,
        "topics": [],
    }
    retriever = retriever or Mock()
    retriever.execute.return_value = [EVIDENCE]
    adapter = LangChainAgentAdapter(
        context, retriever, model_factory=lambda: model, progress=progress, **kwargs
    )
    return adapter, model, retriever, progress


def execute(adapter, question="question"):
    return adapter.execute(AnswerRequest(adapter.context, question))


def test_native_tools_scoped_deduplicated_and_request_local():
    calls = AIMessage(
        content="",
        tool_calls=[
            native_call("search_docs", {"query": "one"}, "one"),
            native_call("search_docs", {"query": "two", "top_k": 2}, "two"),
            native_call("get_progress", {}, "progress"),
        ],
    )
    adapter, model, retriever, progress = make_adapter(
        [calls, AIMessage(content="Supported answer"), AIMessage(content="Next answer")]
    )
    result = execute(adapter)
    assert result.answer == "Supported answer" and result.status == AgentStatus.COMPLETED
    assert result.evidences == (EVIDENCE,)
    assert [call.top_k for call in result.retrieval_calls] == [3, 2]
    assert [call.chunk_ids for call in result.retrieval_calls] == [("chunk-a",), ("chunk-a",)]
    for entry in retriever.execute.call_args_list:
        query = entry.args[0]
        assert query.user_id == "A" and query.document_ids == ("doc-a",)
    progress.execute.assert_called_once_with(CONTEXT)
    assert all(call.validation == "valid" for call in result.tool_calls)
    assert result.usage is result.abstained is None
    second = execute(adapter)
    assert not second.evidences and second.trace_id != result.trace_id
    safe = json.dumps(asdict(result))
    assert "tool_args" not in safe and "scratchpad" not in safe


@pytest.mark.parametrize(
    "name,args",
    [
        ("unknown-secret-name", {}),
        ("search_docs", {"query": "x", "user_id": "B"}),
        ("search_docs", {"query": "x", "document_ids": ["doc-b"]}),
        ("search_docs", {"query": " "}),
        ("search_docs", {"query": "x", "top_k": 0}),
        ("get_progress", {"user_id": "B"}),
    ],
)
def test_invalid_native_tool_never_runs_business_action(name, args):
    adapter, model, retriever, progress = make_adapter(
        [AIMessage(content="", tool_calls=[native_call(name, args)]), AIMessage(content="Rejected")]
    )
    result = execute(adapter)
    retriever.execute.assert_not_called()
    progress.execute.assert_not_called()
    assert result.tool_calls[0].validation == "invalid"
    assert "unknown-secret-name" not in json.dumps(asdict(result))


def test_no_pseudo_action_dispatch_and_no_invented_evidence():
    adapter, model, retriever, progress = make_adapter(
        [AIMessage(content='Action: search_docs\nAction Input: {"query":"x"}')]
    )
    result = execute(adapter)
    retriever.execute.assert_not_called()
    assert result.evidences == () and result.tool_calls == ()


def test_foreign_retriever_response_never_reaches_model_or_result():
    adapter, model, retriever, _ = make_adapter(
        [
            AIMessage(content="", tool_calls=[native_call("search_docs", {"query": "x"})]),
            AIMessage(content="No evidence"),
        ]
    )
    retriever.execute.return_value = [Evidence("b", "doc-b", "FOREIGN_SECRET", "b.pdf", 1, 1)]
    result = execute(adapter)
    assert result.evidences == () and result.retrieval_calls == ()
    assert result.tool_calls[0].validation == "failed"
    assert "FOREIGN_SECRET" not in str(model.observed_messages)


def test_total_action_budget_across_parallel_batches():
    adapter, model, retriever, progress = make_adapter(
        [
            AIMessage(
                content="",
                tool_calls=[native_call("get_progress", {}, str(i)) for i in range(10)],
            )
        ]
    )
    result = execute(adapter)
    assert result.status == AgentStatus.INCOMPLETE
    assert progress.execute.call_count == len(result.tool_calls) == 5
    assert model.cursor == 1


def test_repeated_loop_stops_after_five_business_actions():
    adapter, model, retriever, progress = make_adapter(
        [AIMessage(content="", tool_calls=[native_call("get_progress", {})])]
    )
    result = execute(adapter)
    assert result.status == AgentStatus.INCOMPLETE and progress.execute.call_count == 5
    assert result.steps == 6


def test_timeout_cancels_native_request_and_never_runs_late_tools():
    adapter, model, retriever, _ = make_adapter(
        [AIMessage(content="", tool_calls=[native_call("search_docs", {"query": "x"})])],
        policy=ExecutionPolicy(timeout_seconds=0.01),
    )
    model.delay_seconds = 1
    with pytest.raises(ProviderUnavailable, match="timed out"):
        execute(adapter)
    assert model.cursor == 0
    retriever.execute.assert_not_called()


@pytest.mark.parametrize(
    "code,error",
    [(401, ProviderAuthenticationError), (429, QuotaExceeded), (500, ProviderUnavailable)],
)
def test_provider_failures_are_redacted_and_not_retried(code, error):
    failure = RuntimeError("SECRET_API_TOKEN")
    failure.status_code = code
    adapter, model, _, _ = make_adapter([failure])
    with pytest.raises(error) as caught:
        execute(adapter)
    assert "SECRET_API_TOKEN" not in str(caught.value) and model.cursor == 1


def test_malformed_json_native_response_is_rejected():
    adapter, model, _, _ = make_adapter(
        [
            AIMessage(
                content="",
                invalid_tool_calls=[
                    {"name": "search_docs", "args": "{bad", "id": "bad", "error": "secret"}
                ],
            )
        ]
    )
    with pytest.raises(ProviderUnavailable, match="Invalid native"):
        execute(adapter)


def test_context_mismatch_is_rejected_before_model_construction():
    adapter, model, _, _ = make_adapter([AIMessage(content="x")])
    with pytest.raises(EvidenceNotFound):
        adapter.execute(AnswerRequest(AppContext("B", ("doc-b",)), "question"))
    assert model.cursor == 0


def test_text_only_model_is_not_a_native_chat_model():
    adapter, model, _, _ = make_adapter([AIMessage(content="x")])
    adapter.model_factory = lambda: Mock()
    with pytest.raises(ProviderUnavailable, match="Native chat model required"):
        execute(adapter)


def test_concurrent_sessions_keep_scope_evidence_and_trace_isolated():
    async def run():
        adapters = []
        for user, doc in [("A", "doc-a"), ("B", "doc-b"), ("A", "doc-a")]:
            adapter, model, retriever, _ = make_adapter(
                [
                    AIMessage(content="", tool_calls=[native_call("search_docs", {"query": doc})]),
                    AIMessage(content="done"),
                ],
                context=AppContext(user, (doc,)),
            )
            retriever.execute.return_value = [Evidence(doc, doc, user, "fixture.pdf", 1, 1)]
            model.delay_seconds = 0.01
            adapters.append(adapter)
        results = await asyncio.gather(
            *(adapter.aexecute(AnswerRequest(adapter.context, "q")) for adapter in adapters)
        )
        assert [result.evidences[0].text for result in results] == ["A", "B", "A"]
        assert len({result.trace_id for result in results}) == 3

    asyncio.run(run())


def test_usage_only_when_observed_for_every_model_call_and_reasoning_is_filtered():
    usage = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
    adapter, _, _, _ = make_adapter(
        [
            AIMessage(
                content=[
                    {"type": "reasoning", "reasoning": "PRIVATE_THOUGHT"},
                    {"type": "text", "text": "Answer"},
                ],
                usage_metadata=usage,
            )
        ]
    )
    result = execute(adapter)
    assert result.answer == "Answer" and result.usage.input_tokens == 10
    assert result.usage.cost_usd is None
