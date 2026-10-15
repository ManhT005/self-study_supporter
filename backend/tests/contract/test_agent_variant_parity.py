from unittest.mock import Mock

import pytest

pytest.importorskip("langchain")

from langchain_core.messages import AIMessage

from scripts.langchain_fixtures import ScriptedNativeModel, native_call
from study_supporter.application.contracts.agent import AgentResult, AgentStatus
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest
from study_supporter.application.contracts.retrieval import Evidence
from study_supporter.application.ports.llm import ChatResponse
from study_supporter.application.use_cases.answer_question import AnswerQuestionUseCase
from study_supporter.orchestration.langchain_agent.adapter import LangChainAgentFactory
from study_supporter.orchestration.legacy_react.adapter import LegacyReActAdapter


@pytest.mark.parametrize("variant", ["legacy", "langchain"])
def test_agent_variants_share_core_result_and_answer_contract(variant):
    context = AppContext("A", ("a",))
    retriever, llm = Mock(), Mock()
    evidence = Evidence("one", "a", "fixture", "fixture.pdf", 1, 1)
    retriever.execute.return_value = [evidence]
    if variant == "legacy":
        llm.chat.side_effect = [
            ChatResponse('Action: search_docs\nAction Input: {"query":"fixture"}'),
            ChatResponse("Final Answer: supported"),
        ]
        factory = LegacyReActAdapter
    else:
        factory = LangChainAgentFactory(
            lambda: ScriptedNativeModel(
                responses=[
                    AIMessage(
                        content="", tool_calls=[native_call("search_docs", {"query": "fixture"})]
                    ),
                    AIMessage(content="supported"),
                ]
            ),
            Mock(),
        )
    agent = factory(context, llm, retriever, lambda: [])
    request = AnswerRequest(context, "question")
    result = agent.execute(request)
    assert isinstance(result, AgentResult) and result.status == AgentStatus.COMPLETED
    assert result.evidences == (evidence,) and result.answer == "supported"
    assert result.usage is result.abstained is None
    assert result.retrieval_calls[0].chunk_ids == ("one",)
    # Recreate the request-local agent to exercise the unchanged use case.
    if variant == "legacy":
        llm.chat.side_effect = [ChatResponse("Final Answer: supported")]
    answer = AnswerQuestionUseCase(factory(context, llm, retriever, lambda: []), context).execute(
        request
    )
    assert answer.answer == "supported" and answer.trace_id
