import json
import re

from pydantic import ValidationError
from src.llm.json_ultis import parse_llm_model
from src.llm.llm_adapter import LLMAdapter
from src.graph.schemas import ConceptGraph


GRAPH_EXTRACTION_PROMPT = """Dựa trên nội dung tài liệu học tập sau, hãy trích xuất các khái niệm chính
và quan hệ tiên quyết giữa chúng (khái niệm nào cần hiểu trước khái niệm nào).

Nội dung:
{content}

Chỉ trả về JSON, KHÔNG thêm markdown code fence, đúng format:
{{
  "nodes": [{{"id": "...", "label": "...", "description": "..."}}],
  "edges": [{{"source": "id_khai_niem_truoc", "target": "id_khai_niem_sau"}}]
}}

Giới hạn tối đa 10 khái niệm chính, không cần quá chi tiết.
"""


def build_concept_graph(content: str, llm: LLMAdapter) -> ConceptGraph:
    prompt = GRAPH_EXTRACTION_PROMPT.format(content=content)
    response = llm.chat([{"role": "user", "content": prompt}])

    # TODO:
    # 1. Dọn markdown code fence nếu có (tái sử dụng logic giống
    #    GenerateQuizTool._strip_markdown_fence — cân nhắc tách thành hàm
    #    dùng chung ở đâu đó thay vì copy-paste, ví dụ src/llm/json_utils.py)
    # 2. json.loads(...) -> dict
    # 3. ConceptGraph(**dict đó) -> validate qua Pydantic
    # 4. Bọc try/except (json.JSONDecodeError, ValidationError) -> nếu lỗi,
    #    trả về ConceptGraph rỗng (nodes=[], edges=[]) thay vì crash toàn bộ
    #    pipeline upload tài liệu chỉ vì graph extraction thất bại
    try:
        return parse_llm_model(response.text, ConceptGraph)   # <-- .text đã sửa
    except (json.JSONDecodeError, ValidationError):
        return ConceptGraph(nodes=[], edges=[])