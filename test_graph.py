import os

from google import genai
from dotenv import load_dotenv

from src.graph.graph_algorithms import detect_cycles, suggest_learning_path
from src.graph.graph_builder import build_concept_graph
from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient
from src.rag.bm25_index import BM25Index
from src.rag.vector_store import VectorStore


load_dotenv()


store = VectorStore()
chunks = store.load_all_chunks()
bm25_index = BM25Index(chunks)

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

llm = GeminiClient(gemini_client, model="gemini-3-flash-preview")

# llm = OllamaClient()


# Lấy vài chunk đầu từ store đã có, hoặc gọi search_docs với truy vấn tổng quát
content = "\n\n".join(c.text for c in chunks[:5])  # vài chunk đầu tài liệu

graph = build_concept_graph(content, llm)
print(f"Số node: {len(graph.nodes)}")
print(f"\nSố edge: {len(graph.edges)}")

cycles = detect_cycles(graph)
print(f"Số cycle phát hiện: {len(cycles)}")
for c in cycles:
    print(f"  Cycle: {' -> '.join(c)} -> {c[0]}")

if not cycles:
    path = suggest_learning_path(graph)
    print("\nThứ tự học đề xuất:")
    for node_id in path:
        node = next(n for n in graph.nodes if n.id == node_id)
        print(f"  {node.label}")
else:
    print("\n⚠️ Không thể sắp xếp lộ trình học vì đồ thị có chu trình.")