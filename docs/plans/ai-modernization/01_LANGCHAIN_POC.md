# Phase 2 — LangChain `create_agent` POC with Existing Tools

**Estimate:** 1 week · **Prerequisite:** Phase 1 benchmark runnable · **Scope:** backend experimental adapter only.
**Success:** native, schema-valid tool calls with current business semantics; no regex parsing or privilege regression.

## 1. Why a POC, not a framework rewrite

Current `ReActOrchestrator` reads free-text `Action:` and `Action Input:` using regex/AST and stops at five steps. LangChain `create_agent` should use provider **native tool-calling**, typed input schemas and existing application use cases. The current legacy orchestrator remains unchanged behind a variant flag for regression comparisons. LangChain is not a replacement for authorization, repositories, retrieval contracts or durable state.

Before implementation, confirm current API on https://docs.langchain.com/oss/python/langchain/agents and **pin compatible LangChain, LangGraph and provider packages in the existing lock generation process**. Reject unsupported provider/model combinations instead of falling back to legacy regex inside the new adapter.

## 2. Preserve four tool contracts

| Tool name | Inputs from model | Bound to authenticated context | Side effects / policy |
|---|---|---|---|
| `search_docs` | `query: nonblank str`, `top_k: int (1..10)` | user ID + owned active documents | read; return structured `Evidence[]` |
| `generate_quiz` | topic/query, `num_questions: int (1..15)` | current document/topic | generation; validate exact schema; don't directly mutate grades |
| `get_progress` | no arbitrary user identifier | authenticated user | read only; return concise summary |
| `save_note` | `note: bounded str` | authenticated user | **write**, validate content and user intent/confirmation policy, idempotency key |

**Observed wrappers:** `backend/src/study_supporter/orchestration/legacy_react/tools/{retrieve_evidence,generate_quiz,get_progress,save_note}.py`. Implement fresh typed wrappers which delegate to existing `application.use_cases`, rather than changing legacy tool behavior during the comparison. `user_id`, `document_ids`, database handle and retriever are **runtime-injected**; they must never appear in model-declared tool arguments.

## 3. Proposed files and contracts

```text
backend/src/study_supporter/
  application/ports/agent.py                  # new AgentPort, request/result contracts
  application/contracts/agent.py              # typed result/event/tool receipt
  orchestration/langchain_agent/{__init__,factory,tools,runner}.py
  infrastructure/llm/langchain_bridge.py      # native tool-call compatible model adapter
  bootstrap.py                                # select variant per deployment/request policy
backend/tests/unit/test_langchain_tools.py
backend/tests/contract/test_agent_variants.py
backend/tests/integration/test_langchain_agent_scopes.py
```

**Important:** keep application/domain independent from LangChain; `AgentPort` is a plain Python interface. Build one `AgentRunner` with two implementations to start (`legacy`, `langchain`) and reuse API DTOs. No import-time model construction or shared user-bound tool caches.

**Sketch (architecture-level pseudocode, not copy/paste API guarantee):**

```python
# request.context comes exclusively from authenticated server middleware
scoped_tools = tool_factory.for_context(request.context)
model = provider_bridge.require_native_tool_calling(request.model_mode)
agent = create_agent(model=model, tools=scoped_tools, system_prompt=SYSTEM_POLICY)
result = invoke_with_budget(agent, request.question, max_steps=5, timeout_s=45)
return map_messages_and_evidence_to_agent_result(result)
```

Use Pydantic/typed schemas at tool boundaries, serialize small bounded results, redact external errors. **Do not expose the model's private scratchpad or chain-of-thought** to frontend/tracing. Tool receipt can show only an activity summary (e.g. “Đã tìm 3 đoạn tài liệu”).

## 4. Implementation sequence

1. **LC-01 | Capability matrix:** Test existing Ollama/cloud adapters for `bind_tools`, parallel tool calls, JSON argument quality and timeouts; record supported model IDs. Provider may be unsupported; POC must detect it.
2. **LC-02 | Contracts:** Add `AgentRequest`, `AgentResult`, `ToolReceipt`, `AgentError`; serialize citations only from the retrieval port; compatible with existing `AnswerResult`.
3. **LC-03 | Typed tools:** Four schemas, deterministic guards, bounded string lengths, conversion to existing use cases; keep identity injected and reject any incoming `user_id`.
4. **LC-04 | Runner:** Model mapping, recursion/step limit 5 by default, timeout and max output tokens, explicit stop/error policy, one retry only for retriable transport/schema failures.
5. **LC-05 | Wiring:** `AI_ORCHESTRATOR=legacy|langchain`, default legacy; no new frontend routes necessary. Add correlation IDs through existing FastAPI endpoint.
6. **LC-06 | Compare:** Run same frozen Phase 1 subset on both adapters (paired); record validity, selection, citation fidelity, cost and latency.
7. **LC-07 | Documentation:** Add a short ADR for native-tool compatibility and version pins, plus a runbook for disabling the flag.

## 5. Security and failure tests

| ID | Scenario | Expected |
|---|---|---|
| LC-T01 | Model requests unknown tool | Typed `TOOL_NOT_ALLOWED`; no dynamic import/exec |
| LC-T02 | Tool args contain forged `user_id` | Rejected/ignored; only server context used |
| LC-T03 | `top_k=999` or empty query | Schema/validation error before retrieval |
| LC-T04 | A requests B document | `EvidenceNotFound`/403 or masked 404; no leaked metadata |
| LC-T05 | Provider emits free-text pseudo JSON | No regex fallback in LangChain mode |
| LC-T06 | `save_note` repeat due to tool retry | idempotent, not two notes; protected write policy |
| LC-T07 | Provider without native tool call | Clearly unsupported → configured fallback or 503 |
| LC-T08 | Infinite tool loop / multi-tool burst | Bounded iterations, rate, total tokens and wall time |
| LC-T09 | Evidence absent | Answer abstains; citations empty |
| LC-T10 | Provider timeout or malformed JSON | Typed error and safe UI text; no secret/traceback leak |

## 6. Exit gate and rollback

- **Proposed gate:** ≥99% valid structured tool dispatch on the labeled POC cases; all ten security/negative tests pass; no cross-user leakage; no regressions against original document/quiz/progress flow.
- Report paired baseline deltas and any unsupported providers. A mere successful single call **does not pass**.
- Disable by setting `AI_ORCHESTRATOR=legacy`; no migration/reindex should be required.
- Defer durable state, complex routes and checkpointing to Phase 3/5. **Next:** [`02_LANGGRAPH_CORE.md`](02_LANGGRAPH_CORE.md).
