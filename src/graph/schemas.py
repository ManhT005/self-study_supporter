from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str                     # slug ngắn gọn, vd "bit", "byte", "ma_hoa_thong_tin"
    label: str                  # tên hiển thị, vd "Bit (Binary Digit)"
    description: str = ""       # mô tả ngắn 1 câu


class GraphEdge(BaseModel):
    source: str                 # id của node tiên quyết (phải học trước)
    target: str                 # id của node phụ thuộc (học sau)


class ConceptGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge] = Field(default_factory=list)