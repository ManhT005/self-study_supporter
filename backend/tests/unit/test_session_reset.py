from apps.streamlit_legacy.session import reset_session_on_logout


def test_logout_drops_all_user_data_and_future_keys():
    keys = [
        "authenticated",
        "user_id",
        "username",
        "vector_store",
        "store",
        "orchestrator",
        "bm25_index",
        "embed_query_fn",
        "current_document_id",
        "graph_source_chunks",
        "quiz_history",
        "pending_prompt",
        "current_sources",
        "progress_db",
        "pdf_upload",
        "new_unknown_account_key",
    ]
    state = dict.fromkeys(keys, object())
    state["theme_mode"] = "dark"
    reset_session_on_logout(state)
    assert state == {"theme_mode": "dark"}


def test_login_as_b_resets_residual_a_state(monkeypatch):
    from apps.streamlit_legacy.components import auth

    state = {"store": "A", "quiz_history": ["A"], "theme_mode": "light"}

    class State(dict):
        def __setattr__(self, key, value):
            self[key] = value

    state = State(state)
    monkeypatch.setattr(auth.st, "session_state", state)
    auth._log_user_in(2, "B")
    assert state == {
        "theme_mode": "light",
        "authenticated": True,
        "user_id": "2",
        "username": "B",
    }
