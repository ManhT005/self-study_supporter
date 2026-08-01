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
from src.eval.rag_only import answer_with_rag_only
from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient
from src.memory.long_term import LongTermMemory
from src.memory.progress_db import ProgressDB
from src.memory.short_term import ShortTermMemory
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

llm = OllamaClient(model="qwen3:4b")

quiz_tool = GenerateQuizTool(llm)


orchestrator = ReActOrchestrator(llm, tools=[tool, quiz_tool, note_tool, progress_tool])

# Test 1: câu hỏi tra cứu -> kỳ vọng gọi search_docs
state1 = orchestrator.run("Đơn vị đo thông tin là gì?")
print("=== Test 1 (nên gọi search_docs) ===")
print(state1.render_scratchpad())
print("\n\nFinal:", state1.final_answer)

# # Test 2: yêu cầu quiz -> kỳ vọng gọi search_docs trước (lấy nội dung) rồi generate_quiz
# state2 = orchestrator.run("Cho tôi 1 câu hỏi trắc nghiệm về đơn vị đo thông tin - bit")
# print("\n=== Test 2 (nên gọi search_docs -> generate_quiz) ===")
# print(state2.render_scratchpad())
# print("\n\nFinal:", state2.final_answer)

# --- Test short-term ---
# stm = ShortTermMemory(max_turns=3)
# stm.add_turn("user", "Đơn vị đo thông tin là gì?")
# stm.add_turn("assistant", "Đơn vị đo thông tin chính là bit.")
# # print("=== Short-term history ===")
# print(stm.get_history())

# --- Test long-term ---
# ltm = LongTermMemory(store, embed_query_fn)  # dùng lại store + embed_query_fn đã có

# ltm.save_note("user_001", "Học sinh hay nhầm giữa bit và byte, cần ôn lại.")
# ltm.save_note("user_001", "Học sinh đã nắm vững khái niệm ASCII.")
# ltm.save_note("user_002", "Học sinh khác, ghi chú không liên quan tới user_001.")

# db = ProgressDB()

# db.record_attempt("user_001", "Đơn vị đo thông tin", "Đơn vị nhỏ nhất là gì?", is_correct=True)
# db.record_attempt("user_001", "Đơn vị đo thông tin", "1 byte = ? bit", is_correct=True)
# db.record_attempt("user_001", "Mã hóa thông tin", "ASCII dùng mấy bit?", is_correct=False)
# db.record_attempt("user_002", "Đơn vị đo thông tin", "1 KB = ? byte", is_correct=True)

# print("=== Summary user_001 ===")
# print(db.get_summary("user_001"))

# print("\n=== Summary user_002 (không được lẫn dữ liệu user_001) ===")
# print(db.get_summary("user_002"))

# print("\n=== Test idempotent: chạy lại script, tổng attempts phải TĂNG thêm 4, không phải reset ===")

# ltm = LongTermMemory(store, embed_query_fn)
# progress_db = ProgressDB()

# note_tool = SaveNoteTool(ltm)
# progress_tool = GetProgressTool(progress_db)

# orchestrator = ReActOrchestrator(
#     llm,
#     tools=[tool, quiz_tool, note_tool, progress_tool],  # đủ cả 4 tool thật
# )

# state = orchestrator.run("Tiến độ học tập của user_001 hiện tại thế nào?")
# Lưu ý: câu hỏi này cần user_id, nhưng câu hỏi tự nhiên của học sinh thường không
# tự nói rõ user_id -> đây là vấn đề để dành xử lý ở Sprint 6 (session_state của
# Streamlit tự động gắn user_id vào mọi câu hỏi trước khi đưa vào Agent)

# print(state.render_scratchpad())
# print("\nFinal:", state.final_answer)

# Câu factual - kỳ vọng cả 2 pipeline đều trả lời tốt
# q_factual = "Một byte bằng bao nhiêu bit và 1 Kilôbai (kB) bằng bao nhiêu byte?"

# rag_only_answer = answer_with_rag_only(q_factual, store, bm25_index, embed_query_fn, llm, top_k=3)
# print("=== RAG-only ===")
# print(rag_only_answer)

# state = orchestrator.run(q_factual)
# print("\n=== Agent+RAG ===")
# print(state.final_answer)