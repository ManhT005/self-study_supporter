import hashlib
import streamlit as st
import tempfile
import os
import time

import google.genai as genai

from src.llm.openai_compatible_client import OpenAICompatibleClient
from src.llm.multi_provider_llm import MultiProviderLLM

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
from src.documents.document_service import (
    create_document, update_document_status, update_document_graph, get_latest_ready_document,
)
from src.graph.schemas import ConceptGraph


def _try_resume_existing_documents():
    """
    Khôi phục pipeline từ tài liệu 'ready' gần nhất của ĐÚNG user này (tra theo
    bảng `documents` trong Postgres) — không còn đoán qua ChromaDB.count() như
    trước. Nhờ có concept_graph_json lưu sẵn, việc khôi phục KHÔNG cần gọi lại
    LLM để build graph — nhanh hơn và không tốn quota.
    """
    if st.session_state.orchestrator is not None:
        return  # đã có sẵn trong phiên này

    user_id_int = int(st.session_state.user_id)
    doc = get_latest_ready_document(user_id_int)
    if doc is None:
        return  # user này chưa có tài liệu 'ready' nào, để upload bình thường

    store = VectorStore(collection_name=doc["chroma_collection_name"])
    if store.count() == 0:
        # Postgres nói 'ready' nhưng ChromaDB rỗng (ví dụ host ephemeral bị wipe
        # dữ liệu) -> không thể tin tưởng, để user upload lại cho chắc.
        return

    chunks = store.load_all_chunks()
    bm25_index = BM25Index(chunks)
    provider = _get_embedding_provider()

    def embed_query_fn(query: str) -> list[float]:
        return provider.embed([query], task_type="RETRIEVAL_QUERY")[0]

    llm = _get_llm_client()
    st.session_state.llm_client = llm

    long_term_memory = LongTermMemory(store, embed_query_fn)
    progress_db = ProgressDB()

    tools = [
        SearchDocsTool(store, bm25_index, embed_query_fn),
        GenerateQuizTool(llm),
        SaveNoteTool(long_term_memory, str(st.session_state.user_id)),
        GetProgressTool(progress_db, str(st.session_state.user_id)),
    ]
    orchestrator = ReActOrchestrator(llm, tools=tools)

    st.session_state.store = store
    st.session_state.bm25_index = bm25_index
    st.session_state.embed_query_fn = embed_query_fn
    st.session_state.orchestrator = orchestrator
    st.session_state.progress_db = progress_db
    st.session_state.current_document_id = doc["id"]
    st.session_state.current_sources = [doc["filename"], "Knowledge graph", "Progress notes"]
    st.session_state.graph_source_chunks = chunks[:5]

    if doc["concept_graph_json"]:
        graph = ConceptGraph(**doc["concept_graph_json"])
        st.session_state.concept_graph = graph
        st.session_state.learning_path = [] if detect_cycles(graph) else suggest_learning_path(graph)
    else:
        st.session_state.concept_graph = None
        st.session_state.learning_path = []


def render_sidebar():
    st.markdown(
        """
        <div class="card" style="margin-bottom:0.6rem; padding:0.7rem 0.8rem;">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.4rem;">
            <span style="font-size:1.5rem;">👤</span>
            <span style="font-size:1rem; color:#1e293b; font-weight:500;">{}</span>
        </div>
        """.format(st.session_state.username),
        unsafe_allow_html=True,
    )

    st.markdown("<div class='card' style='padding:0.7rem 0.8rem; margin-bottom: 0.6rem;'><strong>Model</strong></div>", unsafe_allow_html=True)
    _MODE_OPTIONS = ["Auto (khuyến nghị)", "Gemini", "Ollama"]
    _MODE_MAP = {"Auto (khuyến nghị)": "auto", "Gemini": "gemini", "Ollama": "ollama"}
    _REVERSE_MAP = {"auto": 0, "gemini": 1, "ollama": 2}
    model_label = st.radio(
        "Chọn model",
        options=_MODE_OPTIONS,
        horizontal=True,
        index=_REVERSE_MAP.get(st.session_state.model_choice, 0),
        label_visibility="collapsed",
    )
    new_choice = _MODE_MAP[model_label]

    if new_choice != st.session_state.model_choice and st.session_state.orchestrator is not None:
        st.session_state.model_choice = new_choice
        _rebuild_orchestrator_with_new_llm()
        st.rerun()
    else:
        st.session_state.model_choice = new_choice

    with st.expander("Agent capabilities", expanded=False):
        st.markdown(
            """
            <ul style="margin:0; padding-left:1.2rem;">
                <li>Phân tích tài liệu học tập</li>
                <li>Xây lộ trình học từ knowledge graph</li>
                <li>Gọi công cụ để tra cứu và ghi chú</li>
                <li>Tạo quiz cá nhân hóa</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )

    if "last_uploaded_file_id" not in st.session_state:
        st.session_state.last_uploaded_file_id = None
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    _try_resume_existing_documents()

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



    if st.session_state.is_processing:
        st.info("Processing new document... please wait.")

    if st.session_state.orchestrator is not None:
        st.markdown("<div class='card' style='padding:0.7rem 0.8rem;'><strong>Sources</strong></div>", unsafe_allow_html=True)
        sources = st.session_state.get("current_sources") or ["Uploaded PDF", "Knowledge graph", "Progress notes"]
        for source in sources:
            st.markdown(f"<span class='chip'>{source}</span>", unsafe_allow_html=True)

        st.markdown("<div class='card' style='padding:0.7rem 0.8rem; margin-top:0.3rem;'><strong>Thought log</strong></div>", unsafe_allow_html=True)
        if st.session_state.get("last_scratchpad"):
            st.text_area("Thought log", st.session_state.last_scratchpad, height=120, disabled=True, label_visibility="collapsed")
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
    """Khởi tạo LLM theo lựa chọn của người dùng. Hỗ trợ 3 chế độ: auto / gemini / ollama."""
    choice = st.session_state.model_choice

    if choice == "ollama":
        return OllamaClient(model="qwen2.5:1.5b")

    if choice == "gemini":
        return _build_gemini_client()

    # choice == "auto" → build MultiProviderLLM
    return _build_multi_provider_llm()


def _build_gemini_client():
    """Khởi tạo GeminiClient, fallback Ollama nếu thiếu key."""
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


def _build_multi_provider_llm():
    """
    Build MultiProviderLLM với tất cả provider có API key trong .env.
    Thứ tự ưu tiên: Gemini → Groq → Cerebras → GitHub Models → OpenRouter → Ollama.
    Ollama luôn nằm cuối danh sách làm lưới an toàn.
    """
    providers = []

    # 1. Gemini (chất lượng cao nhất)
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            gemini_client_raw = genai.Client(api_key=gemini_key)
            providers.append(GeminiClient(gemini_client_raw, model="gemini-3-flash-preview"))
        except Exception as e:
            print(f"⚠️ Bỏ qua Gemini (lỗi khởi tạo): {e}")

    # 2. Groq (tốc độ nhanh, RPM khá)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        providers.append(OpenAICompatibleClient(
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            model="llama-3.3-70b-versatile",
            provider_name="Groq",
            max_calls=25,
            period=60.0,
        ))

    # 3. Cerebras (token/ngày lớn)
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key:
        providers.append(OpenAICompatibleClient(
            base_url="https://api.cerebras.ai/v1",
            api_key=cerebras_key,
            model="llama-3.3-70b",
            provider_name="Cerebras",
            max_calls=25,
            period=60.0,
        ))

    # 4. GitHub Models
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        providers.append(OpenAICompatibleClient(
            base_url="https://models.inference.ai.azure.com",
            api_key=github_token,
            model="gpt-4o-mini",
            provider_name="GitHub Models",
            max_calls=10,
            period=60.0,
        ))

    # 5. OpenRouter (tổng hợp model mở)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        providers.append(OpenAICompatibleClient(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model="meta-llama/llama-3.3-70b-instruct:free",
            provider_name="OpenRouter",
            max_calls=15,
            period=60.0,
        ))

    # 6. Ollama cục bộ (luôn có, luôn cuối cùng)
    providers.append(OllamaClient(model="qwen2.5:1.5b"))

    if len(providers) == 1:
        # Chỉ có Ollama — không cần MultiProviderLLM
        st.info("Không tìm thấy API key nào, chỉ dùng Ollama cục bộ.")
        return providers[0]

    provider_names = [MultiProviderLLM._get_provider_name(p) for p in providers]
    print(f"🔄 MultiProviderLLM khởi tạo với {len(providers)} providers: {provider_names}")
    return MultiProviderLLM(providers)


@st.cache_resource
def _get_embedding_provider() -> LocalEmbeddingProvider:
    """Singleton cached — model bge-m3 tải 1 lần duy nhất, giữ nguyên qua mọi session."""
    return LocalEmbeddingProvider()


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
        "graph_source_chunks",
        "current_document_id",
    ]:
        st.session_state.pop(key, None)
    st.session_state.chat_history = []


def trigger_graph_build():
    """Tạo/rebuild lộ trình học đồng bộ — kết quả hiển thị ngay, không cần rerun."""
    chunks_for_graph = st.session_state.get("graph_source_chunks")
    if not chunks_for_graph:
        st.warning("Không có dữ liệu nội dung để xây lộ trình học. Hãy upload lại tài liệu.")
        return

    llm = st.session_state.get("llm_client")
    if llm is None:
        st.warning("Chưa có model sẵn sàng, hãy upload lại tài liệu.")
        return

    st.session_state.graph_build_error = None

    with st.spinner("Đang xây dựng lộ trình học..."):
        try:
            content_sample = "\n\n".join(c.text for c in chunks_for_graph[:5])
            graph = build_concept_graph(content_sample, llm)
            st.session_state.concept_graph = graph
            if not detect_cycles(graph):
                st.session_state.learning_path = suggest_learning_path(graph)
            else:
                st.session_state.learning_path = []

            # Persist to Postgres
            doc_id = st.session_state.get("current_document_id")
            if doc_id and graph and graph.nodes:
                update_document_graph(doc_id, graph.model_dump())
        except Exception as e:
            st.session_state.concept_graph = None
            st.session_state.learning_path = []
            st.session_state.graph_build_error = str(e)

    st.session_state.graph_building = False


def _process_uploaded_file_with_progress(uploaded_file, file_bytes: bytes):
    """Pipeline xử lý tài liệu với progress UI chi tiết từng bước."""
    t_start = time.time()

    user_id_int = int(st.session_state.user_id)
    document_id, collection_name = create_document(user_id_int, uploaded_file.name)
    st.session_state.current_document_id = document_id

    try:
        with st.status("📄 Đang xử lý tài liệu...", expanded=True) as status:
            progress_bar = st.progress(0, text="Bắt đầu...")

            # ── Bước 1: Parse PDF ──────────────────────────────────────
            status.update(label="📄 Đang đọc PDF...")
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
            status.update(label="✂️ Đang tách câu...")
            sentences = flatten_pages_to_sentences(pages)
            status.write(f"✓ Tách được {len(sentences)} câu")
            progress_bar.progress(15, text=f"{len(sentences)} câu đã tách")

            # ── Bước 3: Embed sentences ───────────────────────────────
            status.update(label="🧠 Đang tạo embedding cho câu...")
            provider = _get_embedding_provider()

            def on_embed_progress(current, total):
                # Embed sentences chiếm 15% → 55% (40% tổng)
                pct = 15 + int((current / total) * 40)
                progress_bar.progress(pct, text=f"Embedding câu {current}/{total}...")

            sentences = embed_sentences(
                sentences,
                provider,
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
            status.update(label="💾 Đang lưu vào vector database...")
            # collection_name riêng cho đúng document_id này -> cách ly hoàn toàn
            # với tài liệu của user khác (hoặc tài liệu khác của cùng user).
            store = VectorStore(collection_name=collection_name)
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
                SaveNoteTool(long_term_memory, str(st.session_state.user_id)),
                GetProgressTool(progress_db, str(st.session_state.user_id)),
            ]
            orchestrator = ReActOrchestrator(llm, tools=tools)

            st.session_state.store = store
            st.session_state.bm25_index = bm25_index
            st.session_state.embed_query_fn = embed_query_fn
            st.session_state.orchestrator = orchestrator
            st.session_state.progress_db = progress_db
            st.session_state.current_sources = [uploaded_file.name, "Knowledge graph", "Progress notes"]

            # Cập nhật metadata thật vào Postgres — status='ready' để lần đăng
            # nhập sau (_try_resume_existing_documents) nhận ra và tự khôi phục.
            update_document_status(
                document_id,
                status="ready",
                page_count=parse_result.total_pages,
                chunk_count=len(all_chunks),
            )

            progress_bar.progress(90, text="Agent sẵn sàng!")
            status.write("✓ Agent đã khởi tạo xong — bạn có thể chat ngay!")

            # ── Bước 8: Graph building (đồng bộ) ─────────────────────
            status.update(label="🗺️ Đang xây dựng lộ trình học...")
            st.session_state.graph_source_chunks = chunks[:5]

            try:
                content_sample = "\n\n".join(c.text for c in chunks[:5])
                graph = build_concept_graph(content_sample, llm)
                st.session_state.concept_graph = graph
                if not detect_cycles(graph):
                    st.session_state.learning_path = suggest_learning_path(graph)
                else:
                    st.session_state.learning_path = []

                if document_id and graph and graph.nodes:
                    update_document_graph(document_id, graph.model_dump())

                status.write("✓ Lộ trình học đã tạo xong!")
            except Exception as e:
                st.session_state.concept_graph = None
                st.session_state.learning_path = []
                st.session_state.graph_build_error = str(e)
                status.write(f"⚠ Tạo lộ trình học thất bại: {e}")

            st.session_state.graph_building = False
            progress_bar.progress(95, text="Lộ trình học hoàn tất")

            # ── Hoàn tất ──────────────────────────────────────────────
            elapsed = time.time() - t_start
            progress_bar.progress(100, text=f"Hoàn tất trong {elapsed:.1f}s!")
            status.update(label=f" Tài liệu đã sẵn sàng ({elapsed:.1f}s)", state="complete")

        os.unlink(tmp_path)

    except Exception as e:
        # Đánh dấu 'failed' trong Postgres — tránh document bị kẹt vĩnh viễn ở
        # 'processing' nếu có lỗi giữa chừng (bài học từ bug "learning path treo"
        # trước đó: trạng thái không rõ ràng luôn gây khó debug về sau).
        update_document_status(document_id, status="failed")
        raise