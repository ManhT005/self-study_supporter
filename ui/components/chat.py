import streamlit as st
from src.agent.orchestrator import ReActOrchestrator
from src.llm.ollama_client import OllamaClient


def render_chat():
    st.markdown(
        "<div class='card' style='padding:0.7rem 0.8rem; margin-bottom:0.8rem;'><strong>Chat Assistant</strong><br>Giao tiếp trực tiếp với trợ lý của bạn để hỏi, tóm tắt hoặc tạo quiz.</div>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("pending_prompt"):
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        _handle_message(prompt)
        st.rerun()

    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    else:
        st.markdown("_Nhập câu hỏi để bắt đầu cuộc hội thoại._")

    user_question = st.chat_input("Ask about your lesson...")

    if user_question:
        if st.session_state.orchestrator is None:
            st.session_state.chat_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.markdown(user_question)
            with st.chat_message("assistant"):
                st.markdown("Vui lòng upload PDF để kích hoạt trợ lý học tập.")
            st.session_state.chat_history.append({"role": "assistant", "content": "Vui lòng upload PDF để kích hoạt trợ lý học tập."})
            st.rerun()
        else:
            _handle_message(user_question)
            st.rerun()


def _handle_message(user_question: str) -> None:
    st.session_state.chat_history.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            question_with_context = f"[user_id của học sinh: {st.session_state.user_id}] {user_question}"
            state = _run_with_fallback(st.session_state.orchestrator, question_with_context)

        st.markdown(state.final_answer)
        st.session_state.last_scratchpad = state.render_scratchpad()

        sources = st.session_state.get("current_sources") or ["Uploaded PDF", "Knowledge graph", "Progress notes"]
        chip_html = "".join(f"<span class='chip'>{source}</span>" for source in sources)
        st.markdown(f"<div style='margin-top:0.45rem;'>{chip_html}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append({"role": "assistant", "content": state.final_answer})


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