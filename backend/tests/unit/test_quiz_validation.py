import pytest
from pydantic import ValidationError

from src.agent.tools.generate_quiz import QuizQuestion
from ui.components.quiz_arena import _parse_quiz_from_text


@pytest.mark.parametrize("answer", [None, -1, 4, True, "1"])
def test_invalid_structured_answer(answer):
    with pytest.raises(ValidationError):
        QuizQuestion(
            question="Q?",
            options=["a", "b", "c", "d"],
            correct_answer_index=answer,
            explanation="why",
        )


@pytest.mark.parametrize("options", [["a", "b"], ["a", "b", "c", "d", "e"]])
def test_four_options_required(options):
    with pytest.raises(ValidationError):
        QuizQuestion(question="Q?", options=options, correct_answer_index=0, explanation="why")


@pytest.mark.parametrize(
    "text",
    [
        "Câu 1: Q?\nA. a\nB. b\nC. c\nD. d",
        "Câu 1: Q?\nA. a (Đáp án đúng)\nB. b (Đáp án đúng)\nC. c\nD. d",
        "Câu 1: Q?\nA. a (Đáp án đúng)\nB. b",
        "Câu 1: Q?\nA. incorrect\nB. b\nC. c\nD. d",
        "Câu 1: Q?\nA. a (Đáp án đúng)\nA. b\nC. c\nD. d",
    ],
)
def test_text_parser_fails_closed(text):
    assert _parse_quiz_from_text(text) is None
