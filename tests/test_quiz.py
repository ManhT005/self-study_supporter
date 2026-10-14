from ui.components.quiz_arena import _parse_quiz_from_text


def test_parse_multi_question_quiz_text():
    text = '''
Câu 1: What is 2+2?
A. 3
B. 4 (Đáp án đúng)
C. 5
D. 22
Giải thích: 2+2 là 4.

Câu 2: What is the capital of France?
A. Rome
B. Berlin
C. Paris (Đáp án đúng)
D. Madrid
Giải thích: Paris is the capital of France.
'''

    questions = _parse_quiz_from_text(text)

    assert isinstance(questions, list)
    assert len(questions) == 2
    assert questions[0]["question"] == "What is 2+2?"
    assert questions[0]["options"][1] == "4"
    assert questions[0]["correct_index"] == 1
    assert questions[1]["correct_index"] == 2
