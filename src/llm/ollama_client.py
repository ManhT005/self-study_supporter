import requests
from src.llm.llm_adapter import LLMAdapter, ChatResponse


class OllamaClient(LLMAdapter):
    def __init__(self, model: str = "qwen2.5:1.5b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def chat(self, messages, system_prompt=None, stop_sequences=None) -> ChatResponse:
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        ollama_messages.extend(messages)

        payload = {"model": self.model, "messages": ollama_messages, "stream": False}
        if stop_sequences:
            payload["options"] = {"stop": stop_sequences}   # <-- thêm

        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        
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