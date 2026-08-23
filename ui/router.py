import streamlit as st

PAGES = [
    {"id": "overview", "label": "Tổng quan"},
    {"id": "assistant", "label": "Trợ lý"},
    {"id": "learning", "label": "Lộ trình"},
    {"id": "quiz", "label": "Quiz"},
]


def render_navbar():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "assistant" if st.session_state.orchestrator else "overview"

    nav_cols = st.columns(len(PAGES))
    for col, page in zip(nav_cols, PAGES):
        with col:
            is_active = st.session_state.current_page == page["id"]
            if st.button(
                page["label"], 
                key=f"nav_{page['id']}", 
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.current_page = page["id"]
                st.rerun()

    st.divider()


def render_page_content(render_chat, render_graph_viewer, render_quiz_arena):
    page_id = st.session_state.get("current_page", "overview")

    if page_id == "overview":
        st.markdown(
            """
            <div class="card" style="padding:0.85rem 0.95rem;">
                <strong>Agent tự chủ có thể làm gì</strong>
                <ul style="margin:0.35rem 0 0 1rem; padding:0;">
                    <li>Phân tích tài liệu đã upload để hiểu nội dung chính.</li>
                    <li>Xây dựng bản đồ khái niệm rút gọn và đề xuất lộ trình học.</li>
                    <li>Sử dụng vòng lặp ReAct để gọi công cụ phù hợp khi cần tra cứu, ghi chú hoặc tạo quiz.</li>
                    <li>Thiết kế quiz và câu hỏi cá nhân hóa dựa trên điểm yếu của người học.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                """
                <div class="card" style="padding:0.8rem 0.9rem;">
                    <strong>Phân tích tài liệu</strong><br>
                    Agent đọc và tóm tắt nội dung chính trước khi trả lời câu hỏi của bạn.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                """
                <div class="card" style="padding:0.8rem 0.9rem;">
                    <strong>Học theo lộ trình</strong><br>
                    Lộ trình học được suy ra từ mối quan hệ tiên quyết giữa các khái niệm.
                </div>
                """,
                unsafe_allow_html=True,
            )

    elif page_id == "assistant":
        render_chat()
    elif page_id == "learning":
        render_graph_viewer()
    elif page_id == "quiz":
        render_quiz_arena()
    else:
        render_chat()