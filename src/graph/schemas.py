from pydantic import BaseModel, Field, model_validator


class GraphNode(BaseModel):
    id: str  # slug ngắn gọn, vd "bit", "byte", "ma_hoa_thong_tin"
    label: str  # tên hiển thị, vd "Bit (Binary Digit)"
    description: str = ""  # mô tả ngắn 1 câu


class GraphEdge(BaseModel):
    source: str  # id của node tiên quyết (phải học trước)
    target: str  # id của node phụ thuộc (học sau)


class ConceptGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_edges(self):
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Duplicate concept ID")
        if any(edge.source not in ids or edge.target not in ids for edge in self.edges):
            raise ValueError("Graph edge references an unknown concept")
        return self
