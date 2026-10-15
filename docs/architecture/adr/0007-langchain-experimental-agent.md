# 0007: Disabled native-tool LangChain experiment

Status: implemented for engineering review; adoption and release approval pending.
Base: develop at 155fd76 (PR #19 merged). Date: 2026-10-15.

Use `langchain.agents.create_agent` behind the existing AgentPort and composition
seam. Framework imports stay in infrastructure/orchestration; Legacy ReAct remains
the default. Each execution constructs its own model, graph, tools and recorder.
No production flag, database migration, vector change or HTTP DTO change.

The implementation-ready plan supersedes the older G3 prerequisite **only for
disabled engineering work**. G3, independent Test Lead review and owner release
approval still block comparative claims and production enablement.

## Compatibility matrix

| Configuration | SDK path | Evidence / availability |
| --- | --- | --- |
| Offline structured double | BaseChatModel + create_agent | Deterministic native multi-call/roundtrip tests; no provider quality claim |
| Ollama qwen2.5:1.5b (existing default) | ChatOllama 1.1.0 | Candidate only; unavailable until explicit endpoint/model probe passes |
| Gemini gemini-2.5-flash-lite | ChatGoogleGenerativeAI 4.0.0 | Candidate only; unavailable until explicit model probe passes |
| Legacy LLMAdapter.chat / OpenAI-compatible text adapters | None | Unsupported for native dispatch; no Action/JSON/regex fallback |
| auto / unknown provider / mismatched capability receipt | None | Rejected before native model construction |

LangChain 1.4.6 and core 1.6.10 resolve with Python 3.11/3.12 and existing
Pydantic 2.10.4. The optional lock preserves shared dev/API constraints. Google
integration 4.0.0 requires google-genai >=1.53,<2, compatible with the existing
1.56.0 pin; newer 4.4.2 requires >=2.20 and is deliberately excluded.

Run `python -m scripts.langchain_probe` offline. Manual live examples:

```powershell
python -m scripts.langchain_probe --live --provider ollama --model qwen2.5:1.5b
python -m scripts.langchain_probe --live --provider gemini --model gemini-2.5-flash-lite
```

No dotenv loading, model auto-selection or fallback. Cloud credentials must be
explicitly present in GEMINI_API_KEY. Probe uses synthetic data, two requests
maximum, 45 seconds total, no retries, no persistence. Record the returned model
identity plus Ollama model digest/provider revision separately: a tag can move.
Parallel calls and observed usage are reported separately. Missing usage is null.
Failures yield sanitized unavailable receipts. A successful probe establishes
protocol compatibility, not answer quality or release approval.

## Boundaries and rollback

Use request-local tools scoped by authenticated AppContext. Deny unknown fields,
cap tool actions and elapsed time, and never send raw errors, reasoning or tool
arguments into AgentResult. A capability receipt is operator-supplied composition
evidence, not a client credential or a model-editable input.

Rollback: remove the explicit experimental agent_factory injection and uninstall
the optional overlay in the experiment environment. The unchanged default runs
LegacyReActAdapter. No data restoration or migration is necessary.

References: [agents](https://docs.langchain.com/oss/python/langchain/agents),
[Ollama](https://docs.langchain.com/oss/python/integrations/chat/ollama),
[Gemini](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai).
