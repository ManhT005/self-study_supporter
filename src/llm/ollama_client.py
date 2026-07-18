import requests
from src.llm.llm_adapter import LLMAdapter, ChatResponse


class OllamaClient(LLMAdapter):
    def __init__(self, model: str = "qwen2.5:1.5b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def chat(self, messages: list[dict], system_prompt: str | None = None) -> ChatResponse:
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
            },
            timeout=300,  # model local có thể chậm, nhất là lần đầu load vào VRAM/RAM
        )
        response.raise_for_status()
        data = response.json()

        return ChatResponse(
            text=data["message"]["content"],
            usage={
                "input_tokens": data.get("prompt_eval_count"),
                "output_tokens": data.get("eval_count"),
                "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
            },
            finish_reason=data.get("done_reason"),
            raw=data,
        )