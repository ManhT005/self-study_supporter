import streamlit as st

def render_chat():
    if st.session_state.orchestrator is None:
        st.info("👈 Hãy upload tài liệu ở sidebar bên trái trước.")
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
                # Chèn user_id vào câu hỏi để tool get_progress/save_note dùng được
                # (đây chính là cơ chế tự động gắn user_id đã note từ Sprint 4 —
                # thay vì bắt học sinh gõ ID, ta tiêm nó vào ngữ cảnh câu hỏi)
                question_with_context = (
                    f"[user_id của học sinh: {st.session_state.user_id}] {user_question}"
                )
                state = st.session_state.orchestrator.run(question_with_context)

            st.markdown(state.final_answer)
            st.session_state.last_scratchpad = state.render_scratchpad()  # để Thought Log sidebar đọc

        st.session_state.chat_history.append({"role": "assistant", "content": state.final_answer})
        st.rerun()  # rerun để Thought Log ở sidebar cập nhật ngay