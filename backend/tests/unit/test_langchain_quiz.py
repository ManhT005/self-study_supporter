import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from study_supporter.domain.assessment import QuizList
from study_supporter.infrastructure.llm.langchain_quiz import NativeQuizGenerator
from study_supporter.orchestration.langchain_agent.telemetry import Telemetry


@pytest.mark.parametrize("count,valid", [(1, True), (2, False)])
def test_native_quiz_uses_domain_schema_without_answer_invention(count, valid):
    model = Mock()
    parsed = QuizList(
        questions=[
            {
                "question": "Q?",
                "options": ["a", "b", "c", "d"],
                "correct_answer_index": 2,
                "explanation": "why",
            }
        ]
    )
    structured = model.with_structured_output.return_value
    structured.ainvoke = AsyncMock(
        return_value={"parsed": parsed, "raw": None, "parsing_error": None}
    )
    generator = NativeQuizGenerator(lambda: model)
    telemetry = Telemetry()
    if valid:
        result = asyncio.run(generator.generate("authorized material", count, telemetry))
        assert result.questions[0].correct_answer_index == 2 and telemetry.usage() is None
    else:
        with pytest.raises(ValueError, match="count"):
            asyncio.run(generator.generate("authorized material", count, telemetry))
    model.with_structured_output.assert_called_once_with(
        QuizList, method="json_schema", include_raw=True
    )
    assert structured.ainvoke.await_count == 1
