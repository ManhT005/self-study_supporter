import os
import json
from dotenv import load_dotenv
from google import genai

from src.agent.orchestrator import ReActOrchestrator
from src.agent.prompt_templates import build_react_system_prompt
from src.agent.state import AgentState
from src.agent.tools.generate_quiz import GenerateQuizTool
from src.agent.tools.get_progress import GetProgressTool
from src.agent.tools.save_note import SaveNoteTool
from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient
from src.rag.vector_store import VectorStore
from src.rag.bm25_index import BM25Index
from src.rag.embedding_provider import GeminiEmbeddingProvider, LocalEmbeddingProvider  # hoặc LocalEmbeddingProvider
from src.agent.tools.search_docs import SearchDocsTool

load_dotenv()

# gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# provider = GeminiEmbeddingProvider(gemini_client)
# provider = LocalEmbeddingProvider()


# --- Test AgentState ---
store = VectorStore()
chunks = store.load_all_chunks()
bm25_index = BM25Index(chunks)

provider = LocalEmbeddingProvider()  # <-- khớp với DB hiện tại (1024 chiều)

def embed_query_fn(query: str) -> list[float]:
    return provider.embed([query], task_type="RETRIEVAL_QUERY")[0]

tool = SearchDocsTool(store, bm25_index, embed_query_fn)

# Gemini chỉ dùng cho chat, KHÔNG dùng cho embedding
# gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# llm = GeminiClient(gemini_client, model="gemini-3-flash-preview")

llm = OllamaClient()

quiz_tool = GenerateQuizTool(llm)
note_tool = SaveNoteTool()
progress_tool = GetProgressTool()

orchestrator = ReActOrchestrator(llm, tools=[tool, quiz_tool, note_tool, progress_tool])

# Test 1: câu hỏi tra cứu -> kỳ vọng gọi search_docs
state1 = orchestrator.run("Đơn vị đo thông tin là gì?")
print("=== Test 1 (nên gọi search_docs) ===")
print(state1.render_scratchpad())
print("\n\nFinal:", state1.final_answer)

# Test 2: yêu cầu quiz -> kỳ vọng gọi search_docs trước (lấy nội dung) rồi generate_quiz
state2 = orchestrator.run("Cho tôi 1 câu hỏi trắc nghiệm về đơn vị đo thông tin - bit")
print("\n=== Test 2 (nên gọi search_docs -> generate_quiz) ===")
print(state2.render_scratchpad())
print("\n\nFinal:", state2.final_answer)