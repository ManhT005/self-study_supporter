"""Offline four-tool smoke using disposable SQL, actual use cases and native doubles.

No production settings, credentials, model downloads or persistent data are read.
This exercises engineering integration, not model quality or live capabilities.
"""

import json
import tempfile
from pathlib import Path

from langchain_core.messages import AIMessage

from apps.api.tests.fixtures import FixtureFactory
from scripts.docker_smoke import fixture_pdf
from scripts.langchain_fixtures import ScriptedNativeModel, native_call
from study_supporter.application.contracts.context import AppContext
from study_supporter.application.contracts.learning import AnswerRequest, IngestDocumentRequest
from study_supporter.application.use_cases.learning import GetProgressUseCase, SaveNoteUseCase
from study_supporter.domain.errors import EvidenceNotFound
from study_supporter.infrastructure.llm.langchain_quiz import NativeQuizGenerator
from study_supporter.orchestration.langchain_agent.adapter import LangChainAgentFactory
from study_supporter.orchestration.langchain_agent.policy import ConfirmedNoteWrite


def run_smoke():
    with tempfile.TemporaryDirectory(prefix="study-langchain-poc-") as directory:
        with FixtureFactory(f"sqlite:///{Path(directory) / 'isolated.db'}") as factory:
            a = factory.authentication.register("fixture-alice", "fixture-password")
            b = factory.authentication.register("fixture-bobby", "fixture-password")
            document = factory.ingestion.execute(
                IngestDocumentRequest(a, "fixture.pdf", fixture_pdf())
            )
            context = AppContext(a.user_id, (str(document.document_id),))
            request = AnswerRequest(
                context, "Summarize, show progress, create a quiz and save my confirmed note"
            )
            note = "Explicitly confirmed isolated fixture note."
            approval = ConfirmedNoteWrite(
                context, request.question, note, "fixture-op-1", confirmed=True
            )

            class FixtureNotes:
                def __init__(self):
                    self.saved = []

                def save_note(self, user_id, content):
                    self.saved.append((user_id, content))
                    return "redacted-fixture-id"

            notes = FixtureNotes()
            quiz_value = {
                "questions": [
                    {
                        "question": "Which sentence comes first?",
                        "options": ["First", "Second", "Third", "Fourth"],
                        "correct_answer_index": 0,
                        "explanation": "The fixture starts with First.",
                    }
                ]
            }
            quiz = NativeQuizGenerator(
                lambda: ScriptedNativeModel(responses=[AIMessage(content=json.dumps(quiz_value))])
            )

            def model_factory():
                return ScriptedNativeModel(
                    responses=[
                        AIMessage(
                            content="",
                            tool_calls=[
                                native_call("search_docs", {"query": "First sentence"}, "search"),
                                native_call("get_progress", {}, "progress"),
                                native_call("generate_quiz", {"topic": "First sentence"}, "quiz"),
                                native_call(
                                    "save_note",
                                    {"note": note, "operation_id": "fixture-op-1"},
                                    "note",
                                ),
                            ],
                        ),
                        AIMessage(content="Completed isolated study request."),
                    ]
                )

            factory._agent_factory = LangChainAgentFactory(
                model_factory,
                GetProgressUseCase(factory.progress_repository),
                quiz_generator=quiz,
                notes=SaveNoteUseCase(notes),
                approval_factory=lambda request: approval,
                learning_tools=True,
            )
            # Use the existing composition seam and unchanged answer use case.
            service = factory.answer_service(context, None, lambda: [])
            raw = service.agent.execute(request)
            assert [call.name for call in raw.tool_calls] == [
                "search_docs",
                "get_progress",
                "generate_quiz",
                "save_note",
            ]
            assert all(call.validation == "validated" for call in raw.tool_calls)
            answer = service.execute(request)
            assert answer.evidences and answer.trace_id
            assert all(item.document_id == str(document.document_id) for item in answer.evidences)
            assert notes.saved == [(a.user_id, note)]
            assert len(notes.saved) == 1
            foreign = AppContext(b.user_id, context.active_document_ids)
            denied = factory.answer_service(foreign, None, lambda: []).execute(
                AnswerRequest(foreign, request.question)
            )
            assert denied.evidences == () and len(notes.saved) == 1
            try:
                factory.documents.get(b, document.document_id)
            except EvidenceNotFound:
                pass
            else:
                raise AssertionError("Foreign document access succeeded")
            factory._agent_factory = None
            return {
                "mode": "offline",
                "tools": ["search_docs", "get_progress", "generate_quiz", "save_note"],
                "authorized_writes": len(notes.saved),
                "foreign_evidences": len(denied.evidences),
                "usage": answer.usage,
                "legacy_default": factory._agent_factory is None,
                "status": "passed",
            }


if __name__ == "__main__":
    print(json.dumps(run_smoke()))
