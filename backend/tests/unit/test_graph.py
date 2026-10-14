from study_supporter.ai.graph.algorithms import suggest_learning_path
from study_supporter.domain.knowledge_graph import ConceptGraph, GraphEdge, GraphNode
from study_supporter.ai.assessment.json_parsing import parse_llm_model


def test_parse_llm_model_extracts_json_from_surrounding_text():
    response_text = """
    Tôi đã trích xuất như sau:
    {"nodes": [{"id": "a", "label": "A", "description": "Khái niệm A"}], "edges": []}
    Đây là kết quả cuối cùng.
    """

    graph = parse_llm_model(response_text, ConceptGraph)

    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "a"
    assert graph.nodes[0].label == "A"
    assert graph.edges == []


def test_suggest_learning_path_returns_empty_for_cycles():
    graph = ConceptGraph(
        nodes=[
            GraphNode(id="a", label="Khái niệm A", description=""),
            GraphNode(id="b", label="Khái niệm B", description=""),
        ],
        edges=[
            GraphEdge(source="a", target="b"),
            GraphEdge(source="b", target="a"),
        ],
    )

    path = suggest_learning_path(graph)

    assert path == []
