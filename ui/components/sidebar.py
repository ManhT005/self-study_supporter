import streamlit as st
import tempfile
import os
import google.genai as genai

from src.rag.pdf_parser import parse_pdf
from src.rag.chunker import (
    flatten_pages_to_sentences, embed_sentences,
    compute_distances, compute_breakpoints, group_sentences_into_chunks,
)
from src.rag.embedder import embed_chunks
from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index
from src.rag.embedding_provider import LocalEmbeddingProvider
from src.graph.graph_builder import build_concept_graph
from src.graph.graph_algorithms import detect_cycles, suggest_learning_path

from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient
from src.agent.orchestrator import ReActOrchestrator
from src.agent.tools.search_docs import SearchDocsTool
from src.agent.tools.generate_quiz import GenerateQuizTool
from src.agent.tools.save_note import SaveNoteTool
from src.agent.tools.get_progress import GetProgressTool
from src.memory.long_term import LongTermMemory
from src.memory.progress_db import ProgressDB


def render_sidebar():
    st.caption(f"User ID: `{st.session_state.user_id}`")

    st.divider()
    st.subheader("⚙️ Cấu hình")
    model_label = st.radio(
        "Chọn LLM cho Agent:",
        options=["Gemini (chất lượng cao)", "Ollama local (qwen2.5:1.5b, offline)"],
        index=0 if st.session_state.model_choice == "gemini" else 1,
        # bỏ disabled=...
    )
    new_choice = "gemini" if "Gemini" in model_label else "ollama"

    # Nếu người dùng đổi lựa chọn VÀ đã có orchestrator sẵn -> build lại LLM, giữ nguyên tools/dữ liệu
    if new_choice != st.session_state.model_choice and st.session_state.orchestrator is not None:
        st.session_state.model_choice = new_choice
        _rebuild_orchestrator_with_new_llm()
        st.rerun()
    else:
        st.session_state.model_choice = new_choice

    st.divider()
    uploaded_file = st.file_uploader("Tải lên tài liệu học tập (PDF)", type=["pdf"])

    if uploaded_file is not None and st.session_state.orchestrator is None:
        with st.spinner("Đang xử lý tài liệu... (có thể mất 1-2 phút)"):
            _process_uploaded_file(uploaded_file)
        st.success("Đã sẵn sàng! Hỏi gì đó ở khung chat bên phải.")

    if st.session_state.orchestrator is not None:
        st.divider()
        current_model = "Gemini" if st.session_state.model_choice == "gemini" else "Ollama local"
        st.caption(f"Đang dùng: **{current_model}**")
        st.subheader("🧠 Thought Log")
        if st.session_state.get("last_scratchpad"):
            st.text(st.session_state.last_scratchpad)
        else:
            st.caption("Chưa có hoạt động nào.")


def _rebuild_orchestrator_with_new_llm():
    """Đổi LLM mà KHÔNG re-embed tài liệu — chỉ tạo lại orchestrator + cập nhật tool cần llm riêng."""
    llm = _get_llm_client()

    old_tools = list(st.session_state.orchestrator.tools.values())
    for tool in old_tools:
        if hasattr(tool, "llm"):
            tool.llm = llm

    st.session_state.orchestrator = ReActOrchestrator(llm, tools=old_tools)
def _get_llm_client():
    """Khởi tạo LLM theo lựa chọn của người dùng, fallback Ollama nếu Gemini lỗi cấu hình."""
    if st.session_state.model_choice == "ollama":
        return OllamaClient(model="qwen2.5:1.5b")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.warning("Không tìm thấy GEMINI_API_KEY trong .env, chuyển sang Ollama local.")
        st.session_state.model_choice = "ollama"
        return OllamaClient(model="qwen2.5:1.5b")

    try:
        gemini_client_raw = genai.Client(api_key=api_key)
        return GeminiClient(gemini_client_raw, model="gemini-3-flash-preview")
    except Exception as e:
        st.warning(f"Không khởi tạo được Gemini ({e}), chuyển sang Ollama local.")
        st.session_state.model_choice = "ollama"
        return OllamaClient(model="qwen2.5:1.5b")


def _process_uploaded_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    provider = LocalEmbeddingProvider()

    # RAG pipeline
    pages = parse_pdf(tmp_path)
    sentences = flatten_pages_to_sentences(pages)
    sentences = embed_sentences(sentences, provider)
    distances = compute_distances(sentences)
    breakpoints = compute_breakpoints(sentences, distances, percentile=95)
    chunks = group_sentences_into_chunks(sentences, breakpoints, min_sentences=2, max_chars=800)

    store = VectorStore()
    existing_ids = store.get_existing_ids([c.chunk_id for c in chunks])
    new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
    if new_chunks:
        vectors = embed_chunks(new_chunks, provider)
        store.add_chunks(new_chunks, vectors)

    bm25_index = BM25Index(chunks)

    def embed_query_fn(query: str) -> list[float]:
        return provider.embed([query], task_type="RETRIEVAL_QUERY")[0]

    # LLM theo lựa chọn người dùng
    llm = _get_llm_client()

    # Graph (không chặn app nếu lỗi)
    try:
        content_sample = "\n\n".join(c.text for c in chunks[:5])
        graph = build_concept_graph(content_sample, llm)
        if not detect_cycles(graph):
            st.session_state.learning_path = suggest_learning_path(graph)
        st.session_state.concept_graph = graph
    except Exception:
        st.session_state.concept_graph = None

    # Memory
    long_term_memory = LongTermMemory(store, embed_query_fn)
    progress_db = ProgressDB()

    # Tools + Orchestrator
    tools = [
        SearchDocsTool(store, bm25_index, embed_query_fn),
        GenerateQuizTool(llm),
        SaveNoteTool(long_term_memory),
        GetProgressTool(progress_db),
    ]
    orchestrator = ReActOrchestrator(llm, tools=tools)

    st.session_state.store = store
    st.session_state.bm25_index = bm25_index
    st.session_state.embed_query_fn = embed_query_fn
    st.session_state.orchestrator = orchestrator
    st.session_state.progress_db = progress_db

    os.unlink(tmp_path)