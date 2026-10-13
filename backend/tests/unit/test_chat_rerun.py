from streamlit.testing.v1 import AppTest


def chat_fixture():
    import streamlit as st
    from apps.streamlit_legacy.components.chat import render_chat
    from study_supporter.application.contracts.learning import AnswerResult
    from study_supporter.application.contracts.retrieval import Evidence

    class Session:
        def answer(self, question):
            return AnswerResult(
                "Fixture answer",
                (
                    Evidence(
                        "chunk-a",
                        "doc-a",
                        "content",
                        "fixture.pdf",
                        1,
                        2,
                    ),
                ),
                "fixture-trace",
            )

    st.session_state.setdefault("chat_history", [])
    st.session_state.orchestrator = True
    st.session_state.document_session = Session()
    render_chat()


def test_actual_evidence_survives_chat_reruns():
    app = AppTest.from_function(chat_fixture).run()
    app.chat_input[0].set_value("Question").run()
    assert not app.exception
    assert len(app.session_state["chat_history"]) == 2
    for _ in range(2):
        assert any(
            "fixture.pdf" in block.value and "chunk-a" in block.value for block in app.markdown
        )
        app.run()
        assert not app.exception
