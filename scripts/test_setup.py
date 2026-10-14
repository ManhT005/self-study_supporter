# scripts/test_setup.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import EmbedContentConfig

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    result = client.models.embed_content(
        model="gemini-embedding-001",   # <-- đổi lại đúng model này
        contents="Xin chào, đây là test embedding.",
        config=EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    vector = result.embeddings[0].values
    print("✅ Kết nối API thành công!")
    print("Vector length:", len(vector))
    print("5 giá trị đầu:", vector[:5])
except Exception as e:
    print("❌ Lỗi gọi API:")
    print(e)