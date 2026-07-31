from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import uuid

from ui.components.sidebar import render_sidebar
from ui.components.chat import render_chat  # sẽ tạo ở bước dưới

st.set_page_config(page_title="AI Study Agent", layout="wide")

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
    st.session_state.model_choice = "gemini"  # mặc định, người dùng có thể đổi trước khi upload

# --- Layout 3 cột ---
col_sidebar, col_main, col_right = st.columns([1, 2, 1])

with col_sidebar:
    st.header("📚 Tài liệu & Nhật ký")
    render_sidebar()

with col_main:
    st.header("💬 Hỏi đáp")
    render_chat()

with col_right:
    st.header("🗺️ Lộ trình & Quiz")
    st.caption("(sẽ làm ở Checkpoint 4-5)")