# src/rag/embedding_provider.py
import time
from abc import ABC, abstractmethod
from collections import deque


class RateLimiter:
    """Đảm bảo không gửi quá `max_calls` request trong `period` giây gần nhất."""
    def __init__(self, max_calls: int = 90, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()

    def wait_if_needed(self):
        now = time.time()
        while self.calls and now - self.calls[0] > self.period:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0]) + 0.5
            print(f"⏳ Gần chạm rate limit, tạm dừng {sleep_time:.1f}s...")
            time.sleep(sleep_time)
        self.calls.append(time.time())


def _extract_retry_delay(e, default: float = 30.0) -> float:
    try:
        details = e.response_json.get("error", {}).get("details", [])
        for d in details:
            if d.get("@type", "").endswith("RetryInfo"):
                return float(d["retryDelay"].rstrip("s")) + 3
    except Exception:
        pass
    return default


class EmbeddingProvider(ABC):
    """Interface chung — mọi nơi trong pipeline chỉ nói chuyện qua interface này."""

    @abstractmethod
    def embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        """
        task_type: "RETRIEVAL_DOCUMENT" | "RETRIEVAL_QUERY" | "SEMANTIC_SIMILARITY"
        Provider nào không phân biệt task_type thì tự bỏ qua tham số này bên trong.
        """
        ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, client, batch_size: int = 20, max_retries: int = 5):
        from google.genai.types import EmbedContentConfig
        from google.genai.errors import ClientError
        self.client = client
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(max_calls=90, period=60.0)
        self._EmbedContentConfig = EmbedContentConfig
        self._ClientError = ClientError

    def embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            for attempt in range(self.max_retries):
                self.rate_limiter.wait_if_needed()
                try:
                    result = self.client.models.embed_content(
                        model="gemini-embedding-001",
                        contents=batch,
                        config=self._EmbedContentConfig(
                            task_type=task_type, output_dimensionality=768
                        ),
                    )
                    all_embeddings.extend([e.values for e in result.embeddings])
                    break
                except self._ClientError as e:
                    if getattr(e, "status_code", None) == 429 and attempt < self.max_retries - 1:
                        wait = _extract_retry_delay(e)
                        print(f"429 (batch {i//self.batch_size}), đợi {wait:.1f}s...")
                        time.sleep(wait)
                    else:
                        raise
        return all_embeddings


class LocalEmbeddingProvider(EmbeddingProvider):
    """Chạy local/Kaggle bằng sentence-transformers, không rate limit, không tốn tiền."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        # bge-m3 không phân biệt task_type qua tham số, mà qua prefix câu (tùy chọn nâng cao sau)
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()