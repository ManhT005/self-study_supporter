"""Native structured response doubles; never selectable by production settings."""

import asyncio
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class ScriptedNativeModel(BaseChatModel):
    responses: list[Any] = Field(default_factory=list)
    cursor: int = 0
    delay_seconds: float = 0

    @property
    def _llm_type(self):
        return "offline-native-fixture"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        response = self.responses[min(self.cursor, len(self.responses) - 1)]
        self.cursor += 1
        if isinstance(response, Exception):
            raise response
        return ChatResult(generations=[ChatGeneration(message=response.model_copy(deep=True))])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        return self._generate(messages, stop, run_manager, **kwargs)


def native_call(name, args, call_id="fixture-call"):
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


def capability_model():
    return ScriptedNativeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    native_call("capability_echo", {"value": 1}, "one"),
                    native_call("capability_echo", {"value": 2}, "two"),
                ],
            ),
            AIMessage(content="Echo roundtrip completed."),
        ]
    )
