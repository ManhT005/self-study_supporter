import hashlib
import html
import streamlit as st
from study_supporter.application.contracts.context import AppContext
from study_supporter.domain.errors import DocumentUnsupported, EmbeddingUnavailable
from apps.streamlit_legacy.application_bridge import get_application_services


def _activate_session(session):
    st.session_state.document_session = session
    st.session_state.orchestrator = session  # Presentation readiness sentinel; not an agent/driver.
    if session is not None:
        previous_mode = st.session_state.model_choice
        st.session_state.model_choice = session.mode
        if session.notice:
            (st.warning if previous_mode == "gemini" else st.info)(session.notice)
        st.session_state.current_document_id = session.document["id"]
        st.session_state.current_sources = [session.document["filename"]]
        st.session_state.graph_source_chunks = session.chunks[:5]
        st.session_state.concept_graph = session.graph
        st.session_state.learning_path = session.learning_path


def _try_resume_existing_documents(document_id=None):
    if st.session_state.orchestrator is not None:
        return
    _activate_session(
        get_application_services().open_document(
            AppContext(str(st.session_state.user_id)), document_id, st.session_state.model_choice
        )
    )


def _rebuild_orchestrator_with_new_llm():
    _activate_session(
        get_application_services().open_document(
            AppContext(str(st.session_state.user_id)),
            st.session_state.get("current_document_id"),
            st.session_state.model_choice,
        )
    )


def trigger_graph_build():
    session = st.session_state.get("document_session")
    if session is None:
        st.warning("Không có dữ liệu nội dung để xây lộ trình học. Hãy upload lại tài liệu.")
        return
    st.session_state.graph_build_error = None
    with st.spinner("Đang xây dựng lộ trình học..."):
        try:
            graph, path = session.build_graph()
            st.session_state.concept_graph = graph
            st.session_state.learning_path = path
        except Exception:
            st.session_state.concept_graph = None
            st.session_state.learning_path = []
            st.session_state.graph_build_error = (
                "Không tạo được lộ trình học. Kiểm tra cấu hình AI rồi thử lại."
            )
    st.session_state.graph_building = False


def render_sidebar():
    st.markdown(
        """
        <div class="card" style="margin-bottom:0.6rem; padding:0.7rem 0.8rem;">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-top:0.4rem;">
            <span style="font-size:1.5rem;">👤</span>
            <span style="font-size:1rem; color:#1e293b; font-weight:500;">{}</span>
        </div>
        """.format(html.escape(st.session_state.username)),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='card' style='padding:0.7rem 0.8rem; margin-bottom: 0.6rem;'><strong>Model</strong></div>",
        unsafe_allow_html=True,
    )
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

    uploaded_file = st.file_uploader(
        "Upload PDF", type=["pdf"], label_visibility="collapsed", key="pdf_upload"
    )
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        uploaded_file_id = hashlib.sha256(file_bytes).hexdigest()
        should_process = (
            st.session_state.orchestrator is None
            or uploaded_file_id != st.session_state.last_uploaded_file_id
        )

        if should_process:
            st.session_state.is_processing = True
            try:
                _process_uploaded_file_with_progress(uploaded_file, file_bytes)
            except (DocumentUnsupported, EmbeddingUnavailable) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Xử lý tài liệu thất bại. Kiểm tra database và cấu hình AI rồi thử lại.")
            else:
                st.session_state.last_uploaded_file_id = uploaded_file_id
                st.session_state.current_page = "assistant"
                st.rerun()
            finally:
                st.session_state.is_processing = False

    if st.session_state.is_processing:
        st.info("Processing new document... please wait.")

    if st.session_state.orchestrator is not None:
        st.markdown(
            "<div class='card' style='padding:0.7rem 0.8rem;'><strong>Sources</strong></div>",
            unsafe_allow_html=True,
        )
        sources = st.session_state.get("current_sources") or []
        for source in sources:
            st.markdown(
                f"<span class='chip'>{html.escape(source)}</span>",
                unsafe_allow_html=True,
            )

        if st.session_state.get("graph_building"):
            st.caption("Đang xây dựng lộ trình học... (xem chi tiết ở tab Learning Path)")


def _process_uploaded_file_with_progress(uploaded_file, file_bytes):
    from study_supporter.application.contracts.context import AppContext
    from study_supporter.application.contracts.learning import IngestDocumentRequest

    services = get_application_services()
    with st.status("📄 Đang xử lý tài liệu...", expanded=True) as status:
        bar = st.progress(0)

        def on_progress(event):
            percentages = {
                "VALIDATING": 0,
                "PARSING": 10,
                "CHUNKING": 15,
                "EMBEDDING": 55,
                "INDEXING": 80,
                "READY": 100,
                "FAILED": 0,
            }
            bar.progress(percentages[event.stage.value], text=event.message or event.stage.value)

        result = services.ingestion.execute(
            IngestDocumentRequest(
                AppContext(str(st.session_state.user_id)),
                uploaded_file.name,
                file_bytes,
                getattr(uploaded_file, "type", None),
            ),
            on_progress,
        )
        st.session_state.orchestrator = None
        st.session_state.current_document_id = result.document_id
        _try_resume_existing_documents(result.document_id)
        trigger_graph_build()
        status.update(label="Tài liệu đã sẵn sàng", state="complete")
