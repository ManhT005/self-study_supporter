# src/graph/graph_algorithms.py
import networkx as nx
from src.graph.schemas import ConceptGraph


def to_networkx(graph: ConceptGraph) -> nx.DiGraph:
    """Chuyển ConceptGraph (Pydantic) sang networkx.DiGraph để chạy thuật toán đồ thị."""
    g = nx.DiGraph()
    for node in graph.nodes:
        g.add_node(node.id, label=node.label, description=node.description)
    for edge in graph.edges:
        g.add_edge(edge.source, edge.target)
    return g


def detect_cycles(graph: ConceptGraph) -> list[list[str]]:
    """
    Trả về list các chu trình (cycle) tìm thấy trong đồ thị, nếu có.
    Chu trình nghĩa là LLM rút trích ra quan hệ tiên quyết vô lý kiểu
    A cần B, B cần C, C lại cần A -> không thể sắp xếp thứ tự học được.
    """
    g = to_networkx(graph)
    return list(nx.simple_cycles(g))


def suggest_learning_path(graph: ConceptGraph) -> list[str]:
    """
    Trả về thứ tự học đề xuất (list node id) bằng Topological Sort.
    Nếu đồ thị có cycle, không thể sort được -> cần xử lý trước khi gọi hàm này
    (xem cách dùng trong ví dụ test bên dưới).
    """
    g = to_networkx(graph)
    return list(nx.topological_sort(g))