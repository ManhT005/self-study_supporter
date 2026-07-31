import streamlit as st
from src.agent.orchestrator import ReActOrchestrator
from src.llm.ollama_client import OllamaClient


def render_chat():
    if st.session_state.orchestrator is None:
        st.info("👈 Hãy chọn model và upload tài liệu ở sidebar bên trái trước.")
        return

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("Hỏi gì đó về tài liệu...")

    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Đang suy nghĩ..."):
                question_with_context = (
                    f"[user_id của học sinh: {st.session_state.user_id}] {user_question}"
                )
                state = _run_with_fallback(st.session_state.orchestrator, question_with_context)

            st.markdown(state.final_answer)
            st.session_state.last_scratchpad = state.render_scratchpad()

        st.session_state.chat_history.append({"role": "assistant", "content": state.final_answer})
        st.rerun()


def _run_with_fallback(orchestrator, question: str):
    """Fallback ẨN: chỉ kích hoạt khi Gemini hết quota giữa chừng, không cần người dùng thao tác."""
    try:
        return orchestrator.run(question)
    except RuntimeError as e:
        if "quota" not in str(e).lower():
            raise

        st.warning("⚠️ Gemini hết quota hôm nay, tự động chuyển sang Ollama local từ đây trở đi...")
        st.session_state.model_choice = "ollama"

        fallback_llm = OllamaClient(model="qwen2.5:1.5b")
        new_tools = []
        for tool in orchestrator.tools.values():
            if hasattr(tool, "llm"):
                tool.llm = fallback_llm
            new_tools.append(tool)

        fallback_orchestrator = ReActOrchestrator(fallback_llm, tools=new_tools)
        st.session_state.orchestrator = fallback_orchestrator

        return fallback_orchestrator.run(question)