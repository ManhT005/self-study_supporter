from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import uuid

from ui.components.sidebar import render_sidebar, _check_background_graph
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
            padding-top: 0.5rem;
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
            padding-top: 0.45rem;
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

# --- Khởi tạo session_state 1 lần duy nhất khi user mở app ---
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{uuid.uuid4().hex[:8]}"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = None

if "concept_graph" not in st.session_state:
    st.session_state.concept_graph = None

if "model_choice" not in st.session_state:
    st.session_state.model_choice = "gemini"

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


def apply_quick_action(prompt: str) -> None:
    st.session_state.current_page = "assistant"
    st.session_state.pending_prompt = prompt


st.markdown(
    """
    <div class="hero-panel">
        <h2 style="margin: 0 0 0.2rem 0; font-size: 1.35rem;">Self Study Agent</h2>
        <p style="margin: 0; opacity: 0.95;">Tải lên một tài liệu, để agent phân tích nội dung, xây lộ trình học và tạo quiz phù hợp với điểm yếu của bạn.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

_, action_col = st.columns([4, 1])
with action_col:
    button_label = "Dark" if st.session_state.theme_mode == "light" else "Light"
    if st.button(button_label, key="theme_switch", use_container_width=True):
        st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"
        st.rerun()

metrics = st.columns([1, 1, 1])
with metrics[0]:
    st.metric("Status", "Ready" if st.session_state.orchestrator else "Waiting", "")
with metrics[1]:
    st.metric("Model", "Gemini" if st.session_state.model_choice == "gemini" else "Ollama", "")
with metrics[2]:
    st.metric("Learning path", str(len(st.session_state.learning_path)) if st.session_state.learning_path else "0", "")

if st.session_state.orchestrator is not None:
    st.markdown(
        "<div class='card' style='padding:0.75rem 0.85rem; margin-top:0.4rem;'><strong>Agent quick actions</strong></div>",
        unsafe_allow_html=True,
    )
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("Progress", key="quick_progress", use_container_width=True):
            apply_quick_action(f"Cho tôi biết tiến độ học tập của học sinh {st.session_state.user_id}.")
    with action_cols[1]:
        if st.button("Save note", key="quick_note", use_container_width=True):
            apply_quick_action(f"Lưu một ghi chú quan trọng cho học sinh {st.session_state.user_id} liên quan đến nội dung tài liệu vừa upload.")
    with action_cols[2]:
        if st.button("Search docs", key="quick_search", use_container_width=True):
            apply_quick_action("Tìm và tóm tắt các điểm quan trọng liên quan trong tài liệu đã upload.")
    with action_cols[3]:
        if st.button("New quiz", key="quick_quiz", use_container_width=True):
            apply_quick_action("Tạo một quiz ngắn để kiểm tra hiểu biết của tôi.")

with st.sidebar:
    if st.button("Show sidebar" if st.session_state.collapsed_sidebar else "Hide sidebar", use_container_width=True):
        st.session_state.collapsed_sidebar = not st.session_state.collapsed_sidebar
        st.rerun()

    if not st.session_state.collapsed_sidebar:
        render_sidebar()
    else:
        st.markdown("<div class='card'><strong>Workspace</strong><br>Upload a document to unlock the assistant.</div>", unsafe_allow_html=True)
        if st.button("Open workspace", use_container_width=True):
            st.session_state.collapsed_sidebar = False
            st.rerun()

render_navbar()
render_page_content(render_chat, render_graph_viewer, render_quiz_arena)