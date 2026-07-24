import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def strip_markdown_fence(text: str) -> str:
    """Loại bỏ markdown code fence (``` hoặc ```json) nếu có."""

    text = text.strip()

    pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(pattern, text, flags=re.IGNORECASE)

    return match.group(1).strip() if match else text


def parse_llm_json(text: str) -> Any:
    """Parse JSON từ output của LLM."""

    cleaned = strip_markdown_fence(text)
    return json.loads(cleaned)


def parse_llm_model(text: str, model: Type[T]) -> T:
    """Parse output của LLM thành một Pydantic model."""

    data = parse_llm_json(text)
    return model(**data)