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
                state = st.session_state.orchestrator.run(user_question)

            st.markdown(state.final_answer)
            st.session_state.last_scratchpad = state.render_scratchpad()  # để Thought Log sidebar đọc

        st.session_state.chat_history.append({"role": "assistant", "content": state.final_answer})
        st.rerun()  # rerun để Thought Log ở sidebar cập nhật ngay