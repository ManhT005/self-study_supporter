from unittest.mock import Mock

from study_supporter.orchestration.legacy_react.orchestrator import ReActOrchestrator
from study_supporter.application.ports.llm import ChatResponse


def test_react_executes_mock_tool_then_returns_final_answer():
    llm, tool = Mock(), Mock()
    tool.name = "fixture_tool"
    tool.get_schema.return_value = {"parameters": {"properties": {"query": {"type": "string"}}}}
    tool.description = "fixture"
    tool.safe_run.return_value = "evidence"
    llm.chat.side_effect = [
        ChatResponse(text='Thought: search\nAction: fixture_tool\nAction Input: {"query": "test"}'),
        ChatResponse(text="Thought: done\nFinal Answer: answer"),
    ]
    result = ReActOrchestrator(llm, [tool]).run("question")
    assert result.final_answer == "answer"
    tool.safe_run.assert_called_once_with(query="test")


def test_react_invalid_json_never_calls_tool():
    llm, tool = Mock(), Mock()
    tool.name = "fixture_tool"
    tool.get_schema.return_value = {"parameters": {"properties": {"query": {"type": "string"}}}}
    llm.chat.side_effect = [
        ChatResponse(text="Thought: search\nAction: fixture_tool\nAction Input: {broken}"),
        ChatResponse(text="Final Answer: unavailable"),
    ]
    result = ReActOrchestrator(llm, [tool]).run("question")
    assert result.final_answer == "unavailable"
    tool.safe_run.assert_not_called()
