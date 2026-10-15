"""Opt-in native models. Text-only adapters and unprobed configurations fail closed."""

import asyncio
import hashlib
from contextlib import suppress
from dataclasses import dataclass, field

from study_supporter.domain.provider_errors import ProviderUnavailable


@dataclass(frozen=True)
class NativeModelConfig:
    provider: str
    model: str
    base_url: str = "http://localhost:11434"
    api_key: str = field(default="", repr=False)
    timeout_seconds: float = 45
    max_output_tokens: int = 2048

    def __post_init__(self):
        if self.provider not in {"ollama", "gemini"} or not self.model.strip():
            raise ValueError("An explicit Ollama or Gemini model is required")
        if self.model.lower() in {"auto", "latest"} or self.model.endswith(":latest"):
            raise ValueError("Pin the model identity explicitly")
        if not 0 < self.timeout_seconds <= 45 or not 1 <= self.max_output_tokens <= 8192:
            raise ValueError("Invalid native model budget")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Invalid native endpoint")

    @property
    def identity(self) -> tuple[str, str, str]:
        endpoint = self.base_url if self.provider == "ollama" else "google-ai"
        return self.provider, self.model, hashlib.sha256(endpoint.encode()).hexdigest()


@dataclass(frozen=True)
class NativeCapability:
    identity: tuple[str, str, str]
    native_calls: bool
    parallel_calls: bool
    roundtrip: bool
    requests: int
    input_tokens: int | None = None
    output_tokens: int | None = None

    @property
    def available(self):
        return self.native_calls and self.roundtrip


def create_native_model(config: NativeModelConfig):
    """Construct only; no discovery, health check, fallback or model downloads."""
    try:
        if config.provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=config.model,
                base_url=config.base_url,
                temperature=0,
                num_predict=config.max_output_tokens,
                client_kwargs={"timeout": config.timeout_seconds},
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not config.api_key:
            raise ProviderUnavailable("Native provider credentials unavailable")
        return ChatGoogleGenerativeAI(
            model=config.model,
            google_api_key=config.api_key,
            temperature=0,
            max_output_tokens=config.max_output_tokens,
            timeout=config.timeout_seconds,
            # In google-genai 1.56, attempts=0 selects the default five attempts.
            # The LangChain field is forwarded as total attempts, so 1 means no retry.
            max_retries=1,
        )
    except ImportError:
        raise ProviderUnavailable("Install the optional LangChain requirements") from None


def validated_model_factory(config: NativeModelConfig, capability: NativeCapability):
    """The receipt must come from a manual probe of this exact endpoint/model."""
    if capability.identity != config.identity or not capability.available:
        raise ProviderUnavailable("Native tool calling is unavailable for this configuration")
    return NativeModelFactory(config)


@dataclass(frozen=True)
class NativeModelFactory:
    config: NativeModelConfig

    def __call__(self):
        return create_native_model(self.config)

    async def aclose(self, model):
        await close_native_model(model)


async def close_native_model(model):
    """Release request-owned clients using the pinned provider integrations."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_ollama import ChatOllama

    if isinstance(model, ChatOllama):
        with suppress(Exception):
            await model._async_client._client.aclose()
        with suppress(Exception):
            model._client._client.close()
    elif isinstance(model, ChatGoogleGenerativeAI) and model.client is not None:
        with suppress(Exception):
            await model.client.aio.aclose()
        with suppress(Exception):
            model.client.close()
        model.client = None


async def probe_native_model(model, config: NativeModelConfig) -> NativeCapability:
    """Two synthetic requests maximum; never parse text into executable calls."""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, ConfigDict, Field

    class ProbeInput(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)
        value: int = Field(ge=1, le=2)

    tool = StructuredTool.from_function(
        lambda value: str(value),
        name="capability_echo",
        description="Return the given integer.",
        args_schema=ProbeInput,
    )
    first_prompt = HumanMessage(
        content="Call capability_echo twice in one response: value=1 and value=2. Do not answer yet."
    )
    requests = 0
    usage = []
    native = parallel = roundtrip = False
    try:
        async with asyncio.timeout(config.timeout_seconds):
            bound = model.bind_tools([tool])
            requests += 1
            first = await bound.ainvoke([first_prompt])
            usage.append(first.usage_metadata)
            calls = first.tool_calls if isinstance(first, AIMessage) else []
            native = bool(calls) and not first.invalid_tool_calls
            if not native or len(calls) > 2:
                raise ValueError("Native call unavailable")
            values = []
            replies = []
            for call in calls:
                if call["name"] != tool.name or not call.get("id"):
                    raise ValueError("Invalid native call")
                args = ProbeInput.model_validate(call["args"])
                values.append(args.value)
                replies.append(ToolMessage(content=str(args.value), tool_call_id=call["id"]))
            parallel = sorted(values) == [1, 2]
            requests += 1
            final = await bound.ainvoke([first_prompt, first, *replies])
            usage.append(final.usage_metadata)
            roundtrip = (
                isinstance(final, AIMessage)
                and bool(final.content)
                and not final.tool_calls
                and not final.invalid_tool_calls
            )
    except Exception:
        # No provider bodies, prompt, exception text or credentials in the receipt.
        roundtrip = False
    observed = bool(usage) and all(item is not None for item in usage)
    return NativeCapability(
        config.identity,
        native,
        parallel,
        roundtrip,
        requests,
        sum(item["input_tokens"] for item in usage) if observed else None,
        sum(item["output_tokens"] for item in usage) if observed else None,
    )
