"""Fresh scoped closures; never dispatch legacy safe_run or accept account arguments."""

from functools import partial

import anyio
from langchain_core.tools import StructuredTool

from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.orchestration.langchain_agent.models import ProgressInput, SearchInput


async def read_call(function, *args):
    # Read-only IO may finish after cancellation, but cannot publish late evidence.
    return await anyio.to_thread.run_sync(partial(function, *args), abandon_on_cancel=True)


def build_tools(context, retriever, progress, telemetry, policy):
    async def search_docs(query: str, top_k: int = 3):
        request = RetrievalQuery(context.user_id, context.active_document_ids, query, top_k)
        evidence = tuple(await read_call(retriever.execute, request))
        evidence = telemetry.record_retrieval(request, evidence)
        return {
            "evidence": [
                {"number": index, "text": item.text[: policy.snippet_chars]}
                for index, item in enumerate(evidence, 1)
            ]
        }

    async def get_progress():
        summary = await read_call(progress.execute, context)
        return {
            "total_attempts": summary["total_attempts"],
            "correct": summary["correct"],
            "accuracy": summary["accuracy"],
            "topics": [str(topic)[:100] for topic in summary["topics"][:20]],
        }

    return [
        StructuredTool.from_function(
            coroutine=search_docs,
            name="search_docs",
            description="Search authorized study documents. Empty evidence means no support.",
            args_schema=SearchInput,
        ),
        StructuredTool.from_function(
            coroutine=get_progress,
            name="get_progress",
            description="Read the current learner's progress summary.",
            args_schema=ProgressInput,
        ),
    ]
