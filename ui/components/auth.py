import streamlit as st
from src.auth.auth_service import register_user, authenticate_user, AuthError
from src.auth.session import reset_session_on_logout


def render_login_page():
    st.markdown(
        """
        <div style="display:flex; justify-content:center; align-items:center; flex-direction:column; margin-top:2rem; margin-bottom:1rem;">
            <span style="font-size:3.5rem;">🎓</span>
            <h1 style="margin: 0; font-size: 2rem;">Self Study Agent</h1>
            <p style="color: #64748b; font-size: 1rem;">Học tập cá nhân hoá với AI</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập", key="login_username")
                password = st.text_input(
                    "Mật khẩu", type="password", key="login_password"
                )
                submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

            if submitted:
                user_id = authenticate_user(username, password)
                if user_id is None:
                    st.error("Sai tên đăng nhập hoặc mật khẩu.")
                else:
                    _log_user_in(user_id, username)
                    st.rerun()

        with tab_register:
            with st.form("register_form"):
                new_username = st.text_input("Tên đăng nhập", key="register_username")
                new_password = st.text_input(
                    "Mật khẩu", type="password", key="register_password"
                )
                confirm_password = st.text_input(
                    "Xác nhận mật khẩu", type="password", key="register_confirm"
                )
                submitted = st.form_submit_button(
                    "Tạo tài khoản", use_container_width=True
                )

            if submitted:
                if new_password != confirm_password:
                    st.error("Mật khẩu xác nhận không khớp.")
                else:
                    try:
                        user_id = register_user(new_username, new_password)
                        _log_user_in(user_id, new_username)
                        st.success("Tạo tài khoản thành công!")
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))


def _log_user_in(user_id: int, username: str) -> None:
    reset_session_on_logout(st.session_state)
    st.session_state.authenticated = True
    # Giữ dạng string để tương thích các tool/memory hiện có (get_progress,
    # save_note, LongTermMemory...) — chúng vốn được thiết kế nhận user_id kiểu
    # string ngẫu nhiên (uuid), giờ chỉ đổi nguồn gốc chuỗi đó, không đổi kiểu dữ liệu.
    st.session_state.user_id = str(user_id)
    st.session_state.username = username


def render_logout_button():
    if st.button("Đăng xuất", key="logout_btn", use_container_width=True):
        reset_session_on_logout(st.session_state)
        st.rerun()
