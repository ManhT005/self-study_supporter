from dotenv import load_dotenv

load_dotenv()


import streamlit as st
from src.db.lifecycle import verify_schema

try:
    verify_schema()
except Exception:
    st.error("Database chưa sẵn sàng. Chạy migration Alembic theo hướng dẫn trước khi mở ứng dụng.")
    st.stop()

from ui.components.sidebar import render_sidebar
from ui.components.auth import render_login_page, render_logout_button
from ui.components.chat import render_chat
from ui.components.graph_viewer import render_graph_viewer
from ui.components.quiz_arena import render_quiz_arena
from ui.router import render_navbar, render_page_content

st.set_page_config(page_title="Self Study Agent", layout="wide")


def get_theme_styles() -> str:
    if st.session_state.get("theme_mode") == "dark":
        return """
        html, body, .stApp {
            font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        }
        .block-container {
            max-width: 1400px;
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }
        section[data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid #334155;
        }
        .hero-panel {
            background: #111827;
            border: 1px solid #334155;
            color: #f8fafc;
            padding: 0.9rem 1rem;
            border-radius: 14px;
            margin-bottom: 0.7rem;
            box-shadow: 0 2px 8px rgba(2, 6, 23, 0.2);
        }
        .hero-panel p { color: #cbd5e1; margin: 0; }
        .card {
            background: #111827;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            margin-bottom: 0.6rem;
            box-shadow: none;
        }
        .card * { color: #f8fafc !important; }
        .chip {
            display: inline-block;
            background: #1e293b;
            color: #e2e8f0;
            border-radius: 999px;
            padding: 0.22rem 0.55rem;
            margin: 0.2rem 0.25rem 0 0;
            font-size: 0.8rem;
        }
        .stButton > button, .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            border-radius: 999px;
            border: 1px solid #334155;
            background: #111827;
            color: #f8fafc !important;
        }
        .stButton > button:hover {
            border-color: #60a5fa;
            background: #1d4ed8;
            color: white !important;
        }
        .stMarkdown, .stMarkdown * { color: #f8fafc !important; }
        .stChatMessage, .stChatMessage * { color: #f8fafc !important; }
        .stChatMessage > div, .stChatMessage div {
            background: #0f172a !important;
            border: 1px solid #334155 !important;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input,
        textarea, input {
            color: #f8fafc !important;
            background: #111827 !important;
            border: 1px solid #334155 !important;
        }
        """
    return """
        html, body, .stApp {
            font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            background: #f4f7fb;
            color: #0f172a;
            line-height: 1.55;
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, #f8fbff 0%, #f4f7fb 100%);
        }
        div[data-testid="stAppViewContainer"], div[data-testid="stAppViewContainer"] * {
            color: #0f172a !important;
        }
        a, a * { color: #2563eb !important; }
        .stText, .stText *, .stMarkdown, .stMarkdown * {
            color: #0f172a !important;
        }
        .block-container {
            max-width: 1400px;
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }
        section[data-testid="stSidebar"] {
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
        .hero-panel {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.7rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }
        .hero-panel h2 {
            font-size: 1.2rem;
            margin: 0 0 0.2rem 0;
            color: #0f172a;
        }
        .hero-panel p {
            margin: 0;
            color: #475569;
        }
        .card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            margin-bottom: 0.6rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
        }
        .card * { color: #0f172a !important; }
        .chip {
            display: inline-block;
            background: #eef4ff;
            color: #334155;
            border-radius: 999px;
            padding: 0.22rem 0.55rem;
            margin: 0.2rem 0.25rem 0 0;
            font-size: 0.8rem;
        }
        .stButton > button, .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            border-radius: 999px;
            border: 1px solid #dbe4f0;
            background: #ffffff;
            color: #0f172a !important;
        }
        .stButton > button:hover {
            border-color: #93c5fd;
            background: #eff6ff;
            color: #1d4ed8 !important;
        }
        .stChatMessage, .stChatMessage * {
            color: #0f172a !important;
        }
        .stChatMessage > div, .stChatMessage div {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stChatInput"] textarea,
        div[data-testid="stChatInput"] input,
        textarea, input {
            color: #0f172a !important;
            background: #ffffff !important;
            border: 1px solid #dbe4f0 !important;
        }
        """


st.markdown(f"<style>{get_theme_styles()}</style>", unsafe_allow_html=True)

# --- Cổng xác thực: chưa đăng nhập thì không render bất kỳ phần nào của app ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    render_login_page()
    st.stop()

# --- Khởi tạo session_state 1 lần duy nhất khi user đã đăng nhập ---
# (user_id giờ lấy từ tài khoản thật lúc đăng nhập/đăng ký — auth.py đã set sẵn,
# không sinh ngẫu nhiên uuid nữa như trước, để tiến độ học tập nối tiếp đúng người)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

if "concept_graph" not in st.session_state:
    st.session_state.concept_graph = None

if "model_choice" not in st.session_state:
    st.session_state.model_choice = "auto"

if "learning_path" not in st.session_state:
    st.session_state.learning_path = []

if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

if "last_scratchpad" not in st.session_state:
    st.session_state.last_scratchpad = ""

try:
    current_streamlit_theme = st.get_option("theme.base")
except Exception:
    current_streamlit_theme = "light"

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark" if current_streamlit_theme == "dark" else "light"

if "collapsed_sidebar" not in st.session_state:
    st.session_state.collapsed_sidebar = False

if "current_sources" not in st.session_state:
    st.session_state.current_sources = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


hero_col1, hero_col2, hero_col3 = st.columns([7, 2, 1.5])
with hero_col1:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:0.5rem; margin-top: 0.2rem;">
            <span style="font-size:1.6rem;">🎓</span>
            <h2 style="margin: 0; font-size: 1.4rem; color: var(--text-color);">Self Study Agent</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
with hero_col2:
    st.markdown(
        f"<div style='text-align:right; margin-top:0.4rem;'><span style='font-size: 0.95rem; color: #64748b;'>👤 <strong>{st.session_state.get('username', '')}</strong></span></div>",
        unsafe_allow_html=True,
    )
with hero_col3:
    button_label = "🌙 Dark" if st.session_state.theme_mode == "light" else "☀️ Light"
    if st.button(button_label, key="theme_switch", use_container_width=True):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"
        st.rerun()

st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

with st.sidebar:
    if st.button(
        "Show sidebar" if st.session_state.collapsed_sidebar else "Hide sidebar",
        use_container_width=True,
    ):
        st.session_state.collapsed_sidebar = not st.session_state.collapsed_sidebar
        st.rerun()

    if not st.session_state.collapsed_sidebar:
        render_sidebar()
    else:
        st.markdown(
            "<div class='card'><strong>Workspace</strong><br>Upload a document to unlock the assistant.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Open workspace", use_container_width=True):
            st.session_state.collapsed_sidebar = False
            st.rerun()

    st.divider()
    render_logout_button()

render_navbar()
render_page_content(render_chat, render_graph_viewer, render_quiz_arena)
