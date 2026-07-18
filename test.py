import os
from dotenv import load_dotenv
from google import genai
from src.llm.gemini_client import GeminiClient
from src.llm.ollama_client import OllamaClient

load_dotenv()

messages = [{"role": "user", "content": "Việt Nam có bao nhiêu tỉnh thành?"}]

gemini = GeminiClient(
    genai.Client(api_key=os.getenv("GEMINI_API_KEY")),
    model="gemini-3-flash-preview",
)
# res = gemini.chat(messages)
# print("Gemini:", res.text)
# print("Usage:", res.usage, "| finish_reason:", res.finish_reason)

print()

ollama = OllamaClient()
# res2 = ollama.chat(messages)
# print("Ollama:", res2.text)
# print("Usage:", res2.usage, "| finish_reason:", res2.finish_reason)

questions = [
    "Việt Nam có bao nhiêu tỉnh thành?",
    "Giải thích ngắn gọn thuật toán sắp xếp nổi bọt (bubble sort).",
    "Con người có bao nhiêu xương?",
]

for q in questions:
    messages = [{"role": "user", "content": q}]

    import time
    t0 = time.time()
    res_gemini = gemini.chat(messages)
    t1 = time.time()
    res_ollama = ollama.chat(messages)
    t2 = time.time()

    print(f"\n=== {q} ===")
    print(f"Gemini ({t1-t0:.1f}s): {res_gemini.text[:150]}")
    print(f"Ollama ({t2-t1:.1f}s): {res_ollama.text[:150]}")