from study_supporter.ai.assessment.json_parsing import parse_llm_model
from study_supporter.application.ports.llm import LLMAdapter
from study_supporter.domain.knowledge_graph import ConceptGraph


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
        raise RuntimeError("Graph extraction failed: provider returned invalid graph JSON") from e
