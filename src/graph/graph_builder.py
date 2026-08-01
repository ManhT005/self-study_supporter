import json

from pydantic import ValidationError
from src.llm.json_utils import parse_llm_model
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
    try:
        return parse_llm_model(response.text, ConceptGraph)
    except Exception as e:
        raise RuntimeError(
            f"Graph extraction failed: {e}. Model response: {response.text}"
        ) from e