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

## Quiz and note side effects

Read-only composition exposes two tools. Explicit `learning_tools=True` adds
generate_quiz and save_note; it does not approve writes. Quiz content must come
from the authorized retrieval use case, with four-option/index validation using
the existing QuizList/QuizQuestion domain schemas and an exact count check. A
NativeQuizGenerator makes one additional schema request to the explicitly chosen
native model, counted in the total model-call and time budget. The observation
contains only questions/options, excluding the answer key and explanation.

save_note denies by default. A trusted fixture/operator must supply a separately
confirmed ConfirmedNoteWrite grant bound to AppContext, the exact question hash,
normalized note hash, operation ID and five-minute expiry. No HTTP input or model
field can issue approval. The same grant object must be reused for operation
retries. It serializes and reserves the write **before** SaveNoteUseCase IO, so an
ambiguous failure is never automatically retried. Receipts contain only status,
without account, note text or storage ID. This is in-memory idempotency for one
explicit fixture operation, not crash-safe or distributed idempotency.

Native tool batches execute business actions sequentially. Read-only IO uses
cancellable waits; an abandoned read cannot publish late evidence. Writes run
synchronously only against bounded isolated fixture repositories: Python cannot
cancel an already committing synchronous database/vector operation. Production
writes remain disabled, and would require a persistent approval/idempotency
workflow plus transactional deadlines before a separate release decision.

All tool errors, including detailed errors internally returned by LangChain's
ToolNode, are replaced before the next model turn. External LangSmith tracing is
disabled inside the execution context. Provider errors map to the existing safe
authentication/quota/unavailable HTTP boundary without model fallback.
