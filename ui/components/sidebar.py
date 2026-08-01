import hashlib
import streamlit as st
import tempfile
import os
import time
from concurrent.futures import ThreadPoolExecutor, Future

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
    st.markdown(
        """
        <div class="card" style="margin-bottom:0.6rem; padding:0.7rem 0.8rem;">
            <strong>Session</strong><br>
            <span style="font-size:0.9rem; color:#64748b;">{}</span>
        </div>
        """.format(st.session_state.user_id),
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card" style="padding:0.7rem 0.8rem;">
            <strong>Agent capabilities</strong>
            <ul style="margin:0.35rem 0 0 1rem; padding:0;">
                <li>Phân tích tài liệu học tập</li>
                <li>Xây lộ trình học từ knowledge graph</li>
                <li>Gọi công cụ để tra cứu và ghi chú</li>
                <li>Tạo quiz cá nhân hóa</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='card' style='padding:0.7rem 0.8rem;'><strong>Model</strong></div>", unsafe_allow_html=True)
    model_label = st.radio(
        "",
        options=["Gemini", "Ollama"],
        horizontal=True,
        index=0 if st.session_state.model_choice == "gemini" else 1,
    )
    new_choice = "gemini" if model_label == "Gemini" else "ollama"

    if new_choice != st.session_state.model_choice and st.session_state.orchestrator is not None:
        st.session_state.model_choice = new_choice
        _rebuild_orchestrator_with_new_llm()
        st.rerun()
    else:
        st.session_state.model_choice = new_choice

    if "last_uploaded_file_id" not in st.session_state:
        st.session_state.last_uploaded_file_id = None
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed", key="pdf_upload")
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        uploaded_file_id = hashlib.sha256(file_bytes).hexdigest()
        should_process = (
            st.session_state.orchestrator is None
            or uploaded_file_id != st.session_state.last_uploaded_file_id
        )

        if should_process:
            st.session_state.is_processing = True
            _process_uploaded_file_with_progress(uploaded_file, file_bytes)
            st.session_state.last_uploaded_file_id = uploaded_file_id
            st.session_state.is_processing = False
            st.session_state.current_page = "assistant"
            st.rerun()

    # Kiểm tra graph building background đã xong chưa
    _check_background_graph()

    if st.session_state.is_processing:
        st.info("Processing new document... please wait.")

    if st.session_state.orchestrator is not None:
        st.markdown("<div class='card' style='padding:0.7rem 0.8rem;'><strong>Sources</strong></div>", unsafe_allow_html=True)
        sources = st.session_state.get("current_sources") or ["Uploaded PDF", "Knowledge graph", "Progress notes"]
        for source in sources:
            st.markdown(f"<span class='chip'>{source}</span>", unsafe_allow_html=True)

        st.markdown("<div class='card' style='padding:0.7rem 0.8rem; margin-top:0.3rem;'><strong>Thought log</strong></div>", unsafe_allow_html=True)
        if st.session_state.get("last_scratchpad"):
            st.text_area("", st.session_state.last_scratchpad, height=120, disabled=True, label_visibility="collapsed")
        else:
            st.caption("No activity yet")

        if st.session_state.get("graph_building"):
            st.caption("Đang xây dựng lộ trình học... (xem chi tiết ở tab Learning Path)")


def _rebuild_orchestrator_with_new_llm():
    """Đổi LLM mà KHÔNG re-embed tài liệu — chỉ tạo lại orchestrator + cập nhật tool cần llm riêng."""
    llm = _get_llm_client()
    st.session_state.llm_client = llm  # để trigger_graph_build() lấy lại dùng cho thread nền

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


def _get_embedding_provider() -> LocalEmbeddingProvider:
    """Singleton — tránh reload model embedding mỗi lần upload file mới (~2-3s saved)."""
    if "embedding_provider" not in st.session_state:
        st.session_state.embedding_provider = LocalEmbeddingProvider()
    return st.session_state.embedding_provider


def _reset_for_new_document():
    for key in [
        "orchestrator",
        "store",
        "bm25_index",
        "embed_query_fn",
        "concept_graph",
        "learning_path",
        "current_sources",
        "current_quiz",
        "last_scratchpad",
        "graph_building",
        "graph_future",
        "graph_source_chunks",
    ]:
        st.session_state.pop(key, None)
    st.session_state.chat_history = []


def _start_graph_build_from_chunks(chunks_for_graph, llm):
    """Khởi động build graph ở background từ các chunk đã lưu trong session_state.
    `llm` phải là object đã khởi tạo sẵn trên main thread — KHÔNG được gọi bất kỳ
    hàm nào đụng tới st.session_state/st.* bên trong thread nền, vì Streamlit
    không cho phép gọi API của nó từ thread khác ngoài thread chính chạy script
    (lỗi sẽ bị nuốt âm thầm bởi except Exception bên dưới, gây ra tình trạng
    'graph luôn rỗng, không có lỗi nào hiển thị' rất khó debug)."""
    if st.session_state.get("graph_building"):
        return

    st.session_state.concept_graph = None
    st.session_state.learning_path = []
    st.session_state.graph_building = True
    st.session_state.graph_build_error = None
    st.session_state.graph_build_started_at = time.time()

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_build_graph_in_background, chunks_for_graph, llm)
    st.session_state.graph_future = future
    st.session_state.graph_executor = executor


def trigger_graph_build():
    """Trigger tạo/rebuild lộ trình học từ tài liệu đã upload."""
    chunks_for_graph = st.session_state.get("graph_source_chunks")
    if not chunks_for_graph:
        document_text = st.session_state.get("uploaded_document_text")
        if document_text:
            # Tạo chunk tạm từ văn bản hiện có để graph builder vẫn có dữ liệu.
            chunks_for_graph = [type("ChunkPlaceholder", (), {"text": document_text})()]
        else:
            st.warning("Không có dữ liệu nội dung để xây lộ trình học. Hãy upload lại tài liệu.")
            return

    llm = st.session_state.get("llm_client")
    if llm is None:
        st.warning("Chưa có model sẵn sàng, hãy upload lại tài liệu.")
        return

    _start_graph_build_from_chunks(chunks_for_graph, llm)


def _build_graph_in_background(chunks, llm):
    """
    Chạy trong thread riêng — build concept graph không chặn main pipeline.
    `llm` là object LLMAdapter đã khởi tạo sẵn (được truyền vào, KHÔNG tự tạo
    ở đây) — tuyệt đối không gọi st.session_state/st.* trong hàm này.
    """
    try:
        content_sample = "\n\n".join(c.text for c in chunks[:5])
        graph = build_concept_graph(content_sample, llm)
        if not detect_cycles(graph):
            learning_path = suggest_learning_path(graph)
        else:
            learning_path = []
        return graph, learning_path, None
    except Exception as e:
        # Log full traceback to disk for post-mortem and return a concise message
        try:
            import traceback, datetime, os

            tb = traceback.format_exc()
            err_msg = str(e)
            log_line = f"[{datetime.datetime.utcnow().isoformat()}] ERROR: {err_msg}\n{tb}\n\n"
            os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
            with open(os.path.join(os.getcwd(), "data", "graph_build_errors.log"), "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception:
            # best-effort logging; ignore failures here
            pass

        return None, [], f"{e}. See data/graph_build_errors.log for details."


def cancel_stuck_graph_build():
    """Reset trạng thái build graph bị treo quá lâu — cho phép người dùng thử lại
    thay vì kẹt vĩnh viễn ở 'Đang tạo lộ trình học...'."""
    st.session_state.graph_building = False
    st.session_state.graph_build_error = "Đã hủy do build quá lâu, vui lòng thử lại."
    st.session_state.pop("graph_future", None)
    st.session_state.pop("graph_executor", None)


def _check_background_graph():
    """Kiểm tra nếu graph building background đã hoàn thành và cập nhật session_state."""
    future: Future | None = st.session_state.get("graph_future")
    if future is None:
        return

    if future.done():
        try:
            graph, learning_path, error = future.result()
            st.session_state.concept_graph = graph
            st.session_state.learning_path = learning_path
            st.session_state.graph_build_error = error
        except Exception as e:
            st.session_state.concept_graph = None
            st.session_state.learning_path = []
            st.session_state.graph_build_error = str(e)

        # Build finished — clear background handles and mark not building
        st.session_state.graph_building = False
        st.session_state.pop("graph_future", None)
        executor = st.session_state.pop("graph_executor", None)
        try:
            if executor is not None:
                executor.shutdown(wait=False)
        except Exception:
            pass

        # Trigger a rerun so the current page updates immediately with results
        try:
            st.experimental_rerun()
        except Exception:
            # If rerun is not allowed in this context, fall back to leaving session_state updated
            pass
            st.session_state.graph_build_error = str(e)

        st.session_state.graph_building = False
        st.session_state.pop("graph_future", None)
        st.session_state.pop("graph_executor", None)


def _process_uploaded_file_with_progress(uploaded_file, file_bytes: bytes):
    """Pipeline xử lý tài liệu với progress UI chi tiết từng bước."""
    t_start = time.time()

    with st.status(" Đang xử lý tài liệu...", expanded=True) as status:
        progress_bar = st.progress(0, text="Bắt đầu...")

        # ── Bước 1: Parse PDF ──────────────────────────────────────
        status.update(label="Đang đọc PDF...")
        progress_bar.progress(0, text="Đang đọc PDF...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        def on_parse_progress(current, total):
            pct = int((current / total) * 10)  # parse chiếm 10% tổng
            progress_bar.progress(pct, text=f"Đang đọc trang {current}/{total}...")

        parse_result = parse_pdf(tmp_path, on_progress=on_parse_progress)
        pages = parse_result.pages

        status.write(f"✓ Đọc xong: {len(pages)} trang nội dung / {parse_result.total_pages} trang tổng"
                     f" ({parse_result.skipped_pages} trang trắng bỏ qua)")
        progress_bar.progress(10, text="Parse PDF hoàn tất")

        # ── Bước 2: Tách câu ──────────────────────────────────────
        status.update(label="Đang tách câu...")
        sentences = flatten_pages_to_sentences(pages)
        status.write(f"✓ Tách được {len(sentences)} câu")
        progress_bar.progress(15, text=f"{len(sentences)} câu đã tách")

        # ── Bước 3: Embed sentences ───────────────────────────────
        status.update(label="Đang tạo embedding cho câu...")
        provider = _get_embedding_provider()
        parallel_embedding = isinstance(provider, LocalEmbeddingProvider)

        def on_embed_progress(current, total):
            # Embed sentences chiếm 15% → 55% (40% tổng)
            pct = 15 + int((current / total) * 40)
            progress_bar.progress(pct, text=f"Embedding câu {current}/{total}...")

        sentences = embed_sentences(
            sentences,
            provider,
            use_parallel=parallel_embedding,
            max_workers=4,
            on_progress=on_embed_progress,
        )
        status.write(f"✓ Embedded {len(sentences)} câu")
        progress_bar.progress(55, text="Embedding câu hoàn tất")

        # ── Bước 4: Semantic chunking ─────────────────────────────
        status.update(label="🔗 Đang phân đoạn ngữ nghĩa...")
        distances = compute_distances(sentences)
        breakpoints = compute_breakpoints(sentences, distances, percentile=95)
        chunks = group_sentences_into_chunks(sentences, breakpoints, min_sentences=2, max_chars=800)
        status.write(f"✓ Tạo được {len(chunks)} chunk từ {len(breakpoints)} breakpoint")
        progress_bar.progress(65, text=f"{len(chunks)} chunks đã tạo")

        # ── Bước 5: Lưu vào VectorStore ──────────────────────────
        status.update(label="Đang lưu vào vector database...")
        store = VectorStore()
        existing_ids = store.get_existing_ids([c.chunk_id for c in chunks])
        new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]

        if new_chunks:
            def on_chunk_embed_progress(current, total):
                pct = 65 + int((current / total) * 15)
                progress_bar.progress(pct, text=f"Embedding chunk {current}/{total}...")

            vectors = embed_chunks(new_chunks, provider, on_progress=on_chunk_embed_progress)
            store.add_chunks(new_chunks, vectors)
            status.write(f"✓ Lưu {len(new_chunks)} chunk mới (bỏ qua {len(existing_ids)} chunk đã tồn tại)")
        else:
            status.write(f"✓ Tất cả {len(chunks)} chunk đã có trong DB, bỏ qua embedding")

        progress_bar.progress(80, text="Lưu vector database hoàn tất")

        # ── Bước 6: Build BM25 index ─────────────────────────────
        status.update(label="📑 Đang xây BM25 index...")
        all_chunks = store.load_all_chunks()
        bm25_index = BM25Index(all_chunks)
        status.write(f"✓ BM25 index: {len(all_chunks)} chunks")
        progress_bar.progress(85, text="BM25 index hoàn tất")

        # ── Bước 7: Khởi tạo Orchestrator ────────────────────────
        status.update(label="🤖 Đang khởi tạo agent...")

        def embed_query_fn(query: str) -> list[float]:
            return provider.embed([query], task_type="RETRIEVAL_QUERY")[0]

        llm = _get_llm_client()
        st.session_state.llm_client = llm  # để trigger_graph_build() dùng lại đúng LLM này

        long_term_memory = LongTermMemory(store, embed_query_fn)
        progress_db = ProgressDB()

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
        st.session_state.current_sources = [uploaded_file.name, "Knowledge graph", "Progress notes"]

        progress_bar.progress(90, text="Agent sẵn sàng!")
        status.write("✓ Agent đã khởi tạo xong — bạn có thể chat ngay!")

        # ── Bước 8: Graph building (async — không chặn) ──────────
        status.update(label="Đang xây dựng lộ trình học (nền)...")
        st.session_state.concept_graph = None
        st.session_state.learning_path = []
        st.session_state.graph_building = True

        # Snapshot dữ liệu cần cho graph builder
        chunks_for_graph = chunks[:5]
        st.session_state.graph_source_chunks = chunks_for_graph
        st.session_state.uploaded_document_text = "\n\n".join(chunk.text for chunk in chunks_for_graph if getattr(chunk, "text", ""))
        _start_graph_build_from_chunks(chunks_for_graph, llm)

        progress_bar.progress(95, text="Lộ trình học đang xây dựng ở nền...")
        status.write("✓ Lộ trình học đang được xây dựng ở background...")

        # ── Hoàn tất ──────────────────────────────────────────────
        elapsed = time.time() - t_start
        progress_bar.progress(100, text=f"Hoàn tất trong {elapsed:.1f}s!")
        status.update(label=f" Tài liệu đã sẵn sàng ({elapsed:.1f}s)", state="complete")

    os.unlink(tmp_path)