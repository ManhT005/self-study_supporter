from pathlib import Path

path = Path('src/graph/graph_builder.py')
text = path.read_text(encoding='utf-8', errors='replace')
print('----- FILE START -----')
print(text)
print('----- END PREVIEW -----')

idx = text.find('def build_concept_graph')
if idx == -1:
    raise SystemExit('function definition not found')

prefix = text[:idx]
new_func = '''def build_concept_graph(content: str, llm: LLMAdapter) -> ConceptGraph:
    prompt = GRAPH_EXTRACTION_PROMPT.format(content=content)

    response = llm.chat([{"role": "user", "content": prompt}])
    try:
        return parse_llm_model(response.text, ConceptGraph)
    except Exception as e:
        raise RuntimeError(
            f"Graph extraction failed: {e}. Model response: {response.text}"
        ) from e
'''
text = prefix + new_func
path.write_text(text, encoding='utf-8')
print('rewrote function')
