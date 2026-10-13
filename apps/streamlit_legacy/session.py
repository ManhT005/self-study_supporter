from collections.abc import MutableMapping


def reset_session_on_logout(state: MutableMapping) -> None:
    """Drop all account state, including future keys; retain only validated theme."""
    theme = state.get("theme_mode")
    for key in list(state):
        state.pop(key, None)
    if theme in {"light", "dark"}:
        state["theme_mode"] = theme
