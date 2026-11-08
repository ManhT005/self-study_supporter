import asyncio
from dataclasses import fields

import pytest

from study_supporter.application.telemetry import Timing, capture_timings, timed, timing
from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
from study_supporter.application.ports.llm import ChatResponse
from unittest.mock import Mock


def test_nested_timings_preserve_values_and_never_record_private_arguments():
    records = []

    @timed("provider_generation")
    def provider(secret_prompt):
        return secret_prompt

    with capture_timings(records.append) as trace:
        with timing("tool_round"):
            assert provider("PRIVATE-PROMPT") == "PRIVATE-PROMPT"
    assert len(records) == 2
    assert {record.trace_id for record in records} == {trace}
    assert records[0].parent_span_id == records[1].span_id
    assert records[1].parent_span_id is None
    assert all(record.duration_ms >= 0 and record.status == "ok" for record in records)
    assert "PRIVATE" not in repr(records)
    assert {field.name for field in fields(Timing)} == {
        "trace_id",
        "span_id",
        "parent_span_id",
        "operation",
        "duration_ms",
        "status",
    }


def test_failure_records_only_status_and_sink_cannot_mask_application_error():
    records = []
    failure = RuntimeError("PRIVATE-ERROR")
    with capture_timings(records.append):
        with pytest.raises(RuntimeError) as caught:
            with timing("retrieval"):
                raise failure
    assert caught.value is failure
    assert records[0].status == "error"
    assert "PRIVATE" not in repr(records)

    def broken_sink(event):
        raise ValueError("broken metrics")

    with capture_timings(broken_sink):
        with timing("retrieval"):
            pass
        with pytest.raises(RuntimeError) as caught:
            with timing("retrieval"):
                raise failure
        assert caught.value is failure


def test_capture_restores_outer_scope_and_disabled_instrumentation_has_no_events():
    outer, inner = [], []
    with capture_timings(outer.append) as outer_id:
        with timing("open_document"):
            with capture_timings(inner.append) as inner_id:
                with timing("load_all_chunks"):
                    pass
            with timing("bm25_build"):
                pass
    with timing("embedding"):
        pass
    assert len(outer) == 2 and len(inner) == 1
    assert inner_id != outer_id
    assert outer[0].parent_span_id == outer[1].span_id
    assert inner[0].parent_span_id is None
    with pytest.raises(ValueError):
        with timing("user-controlled-label"):
            pass


def test_concurrent_request_scopes_do_not_mix_traces():
    async def request():
        records = []
        with capture_timings(records.append) as trace:
            with timing("retrieval"):
                await asyncio.sleep(0)
        return trace, records

    async def run():
        return await asyncio.gather(request(), request())

    first, second = asyncio.run(run())
    assert first[0] != second[0]
    for trace, records in (first, second):
        assert len(records) == 1 and records[0].trace_id == trace


def test_react_measures_provider_and_tool_without_changing_observations():
    llm, tool = Mock(), Mock()
    tool.name, tool.description, tool.read_only = "fixture_tool", "fixture", True
    tool.get_schema.return_value = {"parameters": {"properties": {}}}
    tool.safe_run.return_value = "PRIVATE OBSERVATION"
    llm.chat.side_effect = [
        ChatResponse("Action: fixture_tool\nAction Input: {}"),
        ChatResponse("Final Answer: answer"),
    ]
    records = []
    with capture_timings(records.append):
        result = ReActOrchestrator(llm, [tool]).run("PRIVATE QUERY")
    assert result.final_answer == "answer"
    assert [record.operation for record in records] == [
        "provider_generation",
        "tool_round",
        "provider_generation",
    ]
    assert "PRIVATE" not in repr(records)
