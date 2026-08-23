import os

from dotenv import load_dotenv
from google import genai

from src.agent.orchestrator import ReActOrchestrator
from src.agent.tools.generate_quiz import GenerateQuizTool
from src.agent.tools.get_progress import GetProgressTool
from src.agent.tools.save_note import SaveNoteTool
from src.agent.tools.search_docs import SearchDocsTool
from src.eval.eval_runner import load_eval_dataset, run_eval, save_results
from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient
from src.memory.long_term import LongTermMemory
from src.memory.progress_db import ProgressDB
from src.rag.bm25_index import BM25Index
from src.rag.embedding_provider import LocalEmbeddingProvider
from src.rag.vector_store import VectorStore


load_dotenv()

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

llm = OllamaClient(model="qwen3:1.7b")

ltm = LongTermMemory(store, embed_query_fn)
progress_db = ProgressDB()

quiz_tool = GenerateQuizTool(llm)

note_tool = SaveNoteTool(ltm)
progress_tool = GetProgressTool(progress_db)

orchestrator = ReActOrchestrator(
    llm,
    tools=[tool, quiz_tool, note_tool, progress_tool],  # đủ cả 4 tool thật
)


dataset = load_eval_dataset()
results = run_eval(dataset[0:5], store, bm25_index, embed_query_fn, llm, orchestrator)  # test 3 câu trước
save_results(results, "data/eval_results_test1.json")

for r in results:
    print(f"[{r['category']}] {r['question']}")
    print(f"  RAG-only ({r['rag_only']['time_sec']}s): {r['rag_only']['answer'][:100]}...")
    print(f"  Agent+RAG ({r['agent_rag']['time_sec']}s, {r['agent_rag']['iterations']} iter): {r['agent_rag']['answer'][:100]}...")
    print()