# ui/components/graph_viewer.py
import streamlit as st

from ui.components.sidebar import trigger_graph_build


def render_graph_viewer():
    graph = st.session_state.get("concept_graph")
    learning_path = st.session_state.get("learning_path")
    has_source_chunks = bool(st.session_state.get("graph_source_chunks"))
    has_uploaded_text = bool(st.session_state.get("uploaded_document_text"))
    has_existing_graph = bool(graph is not None and getattr(graph, "nodes", None))

    if has_source_chunks or has_uploaded_text or has_existing_graph:
        if st.button("Tạo / tạo lại lộ trình học", key="create_learning_path", use_container_width=True):
            trigger_graph_build()
            st.rerun()

    if graph is None or not graph.nodes:
        error = st.session_state.get("graph_build_error")
        if error:
            st.error(f"Xây dựng lộ trình học thất bại: {error}")
        elif st.session_state.get("graph_source_chunks"):
            st.warning("Graph extraction hoàn tất nhưng không tìm thấy khái niệm nào. Có thể LLM trả về kết quả trống hoặc sai định dạng.")
        else:
            st.caption("Chưa có lộ trình học (upload tài liệu hoặc bấm nút phía trên để tạo).")
        return

    if not learning_path:
        st.warning("Đồ thị có chu trình (cycle), không thể sắp xếp lộ trình học tuyến tính.")
        return

    st.markdown("<div style='margin-bottom:0.6rem; color:#475569;'>Lộ trình học được đề xuất dựa trên mối quan hệ tiên quyết giữa các khái niệm.</div>", unsafe_allow_html=True)

    node_map = {n.id: n for n in graph.nodes}
    for i, node_id in enumerate(learning_path, 1):
        node = node_map.get(node_id)
        if node is None:
            continue
        with st.expander(f"{i}. {node.label}", expanded=(i == 1)):
            st.write(node.description or "_(không có mô tả)_")