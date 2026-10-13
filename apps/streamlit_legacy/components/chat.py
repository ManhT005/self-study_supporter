import streamlit as st
import html


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
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": "Vui lòng upload PDF để kích hoạt trợ lý học tập.",
                }
            )
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
            try:
                result = st.session_state.document_session.answer(user_question)
            except RuntimeError as e:
                # Tất cả provider đều hết quota — thông báo cho người dùng
                st.error(f"⚠️ {e}")
                fallback_answer = (
                    "Xin lỗi, tất cả các nhà cung cấp AI đều tạm thời hết quota. "
                    "Vui lòng thử lại sau ít phút hoặc chuyển sang chế độ Ollama cục bộ."
                )
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": fallback_answer}
                )
                return

        st.markdown(result.answer)
        evidence = result.evidences
        sources = [
            f"{item.source} · trang {item.page_start}-{item.page_end} · {item.chunk_id}"
            for item in evidence
        ]
        chip_html = "".join(
            f"<span class='chip'>{html.escape(source)}</span>" for source in sources
        )
        st.markdown(
            f"<div style='margin-top:0.45rem;'>{chip_html}</div>",
            unsafe_allow_html=True,
        )

    st.session_state.chat_history.append({"role": "assistant", "content": result.answer})
