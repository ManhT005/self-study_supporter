from src.agent.tools.generate_quiz import GenerateQuizTool


class DummyLLM:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def chat(self, messages, system_prompt=None, stop_sequences=None):
        return type("Response", (), {"text": self.response_text})()


def test_generate_quiz_uses_the_provided_topic_content():
    quiz_tool = GenerateQuizTool(DummyLLM('{"questions": []}'))

    quiz_tool.run("Nội dung tài liệu về mạng máy tính", num_questions=1)

    assert hasattr(quiz_tool, "last_prompt")
    assert "Nội dung tài liệu về mạng máy tính" in quiz_tool.last_prompt
