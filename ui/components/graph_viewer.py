# ui/components/graph_viewer.py
import streamlit as st


def render_graph_viewer():
    graph = st.session_state.get("concept_graph")
    learning_path = st.session_state.get("learning_path")

    if graph is None or not graph.nodes:
        st.caption("Chưa có lộ trình học (graph extraction có thể đã thất bại hoặc chưa upload tài liệu).")
        return

    if not learning_path:
        st.warning("Đồ thị có chu trình (cycle), không thể sắp xếp lộ trình học tuyến tính.")
        return

    st.caption("Thứ tự học đề xuất, dựa trên quan hệ tiên quyết giữa các khái niệm:")

    node_map = {n.id: n for n in graph.nodes}
    for i, node_id in enumerate(learning_path, 1):
        node = node_map.get(node_id)
        if node is None:
            continue
        with st.expander(f"{i}. {node.label}"):
            st.write(node.description or "_(không có mô tả)_")