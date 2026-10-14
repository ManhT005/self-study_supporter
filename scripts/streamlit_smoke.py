"""Streamlit AppTest: UI registration, logout reset, B login in the same session."""

import uuid

from streamlit.testing.v1 import AppTest

from src.auth.auth_service import register_user


def main():
    marker = uuid.uuid4().hex[:12]
    password = uuid.uuid4().hex
    a, b = f"ui-a-{marker}", f"ui-b-{marker}"
    b_id = register_user(b, password)
    app = AppTest.from_file("main.py", default_timeout=30).run()
    assert not app.exception
    app.text_input(key="register_username").set_value(a)
    app.text_input(key="register_password").set_value(password)
    app.text_input(key="register_confirm").set_value(password)
    next(button for button in app.button if button.label == "Tạo tài khoản").click().run()
    assert not app.exception
    assert app.session_state["username"] == a
    app.session_state["quiz_history"] = {"fixture": ["A private quiz"]}
    app.session_state["vector_store"] = "A private store"
    app.session_state["new_account_scoped_key"] = "A private data"
    app.button(key="logout_btn").click().run()
    assert not app.exception
    for key in ["quiz_history", "vector_store", "new_account_scoped_key"]:
        assert key not in app.session_state
    app.text_input(key="login_username").set_value(b)
    app.text_input(key="login_password").set_value(password)
    next(button for button in app.button if button.label == "Đăng nhập").click().run()
    assert not app.exception
    assert app.session_state["user_id"] == str(b_id)
    assert app.session_state["vector_store"] is None
    assert app.session_state["orchestrator"] is None
    assert "quiz_history" not in app.session_state
    print("PASS: Streamlit UI registration, logout, B login and unknown-key isolation")
    print("AppTest executes Streamlit; a real browser/embedding/LLM flow is separate")


if __name__ == "__main__":
    main()
