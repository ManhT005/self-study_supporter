"""Fresh scoped closures; never dispatch legacy safe_run or accept account arguments."""

from functools import partial

import anyio
from langchain_core.tools import StructuredTool

from study_supporter.application.contracts.retrieval import RetrievalQuery
from study_supporter.domain.assessment import QuizList
from study_supporter.orchestration.langchain_agent.models import (
    ProgressInput,
    QuizInput,
    SaveNoteInput,
    SearchInput,
)
from study_supporter.orchestration.langchain_agent.policy import NoteWriteDenied


async def read_call(function, *args):
    # Read-only IO may finish after cancellation, but cannot publish late evidence.
    return await anyio.to_thread.run_sync(partial(function, *args), abandon_on_cancel=True)


def build_tools(
    context,
    retriever,
    progress,
    telemetry,
    policy,
    *,
    request=None,
    budget=None,
    quiz_generator=None,
    notes=None,
    approval=None,
    learning_tools=False,
):
    async def retrieve(query, top_k):
        retrieval = RetrievalQuery(context.user_id, context.active_document_ids, query, top_k)
        evidence = tuple(await read_call(retriever.execute, retrieval))
        return telemetry.record_retrieval(retrieval, evidence)

    async def search_docs(query: str, top_k: int = 3):
        evidence = await retrieve(query, top_k)
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

    tools = [
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
    if not learning_tools:
        return tools

    async def generate_quiz(topic: str, num_questions: int = 1):
        if quiz_generator is None:
            raise ValueError("Quiz unavailable")
        evidence = await retrieve(topic, 3)
        if not evidence:
            raise ValueError("Quiz requires authorized evidence")
        content = "\n\n".join(item.text[: policy.snippet_chars] for item in evidence)
        budget.take_model_call()
        generated = await quiz_generator.generate(content, num_questions, telemetry)
        # Revalidate at the tool boundary even when composition injects a generator.
        quiz = QuizList.model_validate(
            generated.model_dump() if isinstance(generated, QuizList) else generated
        )
        if len(quiz.questions) != num_questions:
            raise ValueError("Invalid quiz question count")
        return {
            "questions": [
                {"question": q.question[:1000], "options": [opt[:500] for opt in q.options]}
                for q in quiz.questions
            ]
        }

    async def save_note(note: str, operation_id: str | None = None):
        if approval is None:
            raise NoteWriteDenied
        return approval.save(notes, request, note, operation_id, budget)

    tools.extend(
        [
            StructuredTool.from_function(
                coroutine=generate_quiz,
                name="generate_quiz",
                description="Generate a validated quiz from authorized study material, without answers.",
                args_schema=QuizInput,
            ),
            StructuredTool.from_function(
                coroutine=save_note,
                name="save_note",
                description="Save an exact note only when the server has separately confirmed this write.",
                args_schema=SaveNoteInput,
            ),
        ]
    )
    return tools
