"""Hard-bounded subprocess callbacks plugged into the existing paired runner."""

import json
import subprocess
import sys

from evaluation.errors import EvaluationFailure
from evaluation.live.fixtures import write_json
from evaluation.schema import EvaluationCase
from study_supporter.application.contracts.agent import (
    AgentResult,
    AgentStatus,
    AgentUsage,
    RetrievalCall,
    ToolCall,
)
from study_supporter.application.contracts.retrieval import Evidence


def result_from_json(value):
    return AgentResult(
        answer=value["answer"],
        evidences=tuple(Evidence(**e) for e in value["evidences"]),
        trace_id=value["trace_id"],
        status=AgentStatus(value["status"]),
        steps=value["steps"],
        tool_calls=tuple(ToolCall(**c) for c in value["tool_calls"]),
        usage=AgentUsage(**value["usage"]) if value["usage"] else None,
        abstained=value["abstained"],
        retrieval_calls=tuple(
            RetrievalCall(**{**c, "chunk_ids": tuple(c["chunk_ids"])})
            for c in value["retrieval_calls"]
        ),
    )


class LiveCallbacks:
    def __init__(self, fixtures, settings, *, max_calls=6, max_samples=6, worker_timeout=180):
        self.fixtures, self.settings = fixtures, settings
        self.max_calls, self.max_samples, self.worker_timeout = (
            max_calls,
            max_samples,
            worker_timeout,
        )
        self.calls, self.samples, self.blocked = 0, 0, False
        self.telemetry = []
        self.review_answers = []

    def variant(self, name):
        def execute(case):
            self.samples += 1
            metadata = {"case_id": case.case_id, "variant": name, "calls_attempted": 0}
            self.telemetry.append(metadata)
            if self.samples > self.max_samples:
                raise EvaluationFailure("INVALID_SCHEMA")
            with self.fixtures.lease() as root:
                control = root.parent
                journal, output = control / "calls.jsonl", control / "result.json"
                request = control / "request.json"
                case_values = case.model_dump(
                    mode="json",
                    include=set(EvaluationCase.model_fields),
                )
                case_values["annotation_version"] = (
                    "v1"  # worker consumes the stable execution fields, not private votes.
                )
                write_json(
                    request,
                    {
                        "root": str(root),
                        "case": case_values,
                        "variant": name,
                        "journal": str(journal),
                        "settings": {
                            **self.settings,
                            "max_calls": max(0, self.max_calls - self.calls),
                            "provider_blocked": self.blocked,
                        },
                    },
                )
                try:
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "evaluation.live.worker",
                            "--input",
                            str(request),
                            "--output",
                            str(output),
                        ],
                        capture_output=True,
                        timeout=self.worker_timeout,
                        check=False,
                    )
                    value = json.loads(output.read_text(encoding="utf-8"))
                except subprocess.TimeoutExpired:
                    value = {
                        "error_code": "TIMEOUT",
                        "telemetry": {"failure_reason": "WORKER_TIMEOUT"},
                    }
                except (OSError, ValueError):
                    value = {
                        "error_code": "INTERNAL",
                        "telemetry": {"failure_reason": "WORKER_FAILED"},
                    }
                # Durable pre-call reservations count attempts even if the worker is killed mid-request.
                attempted = (
                    len(journal.read_text(encoding="utf-8").splitlines()) if journal.exists() else 0
                )
                self.calls += attempted
                metadata.update(
                    {
                        **value.get("telemetry", {}),
                        "calls_attempted": attempted,
                        "case_id": case.case_id,
                        "variant": name,
                    }
                )
                if metadata.get("failure_reason") in {"PROVIDER_RATE_LIMIT", "PROVIDER_FAILURE"}:
                    self.blocked = True
                if "error_code" in value:
                    raise EvaluationFailure(value["error_code"])
                result = result_from_json(value["result"])
                self.review_answers.append(
                    {
                        "case_id": case.case_id,
                        "variant": name,
                        "answer": result.answer,
                        "evidence": [
                            {
                                "document_id": e.document_id,
                                "chunk_id": e.chunk_id,
                                "text": e.text,
                                "page_start": e.page_start,
                                "page_end": e.page_end,
                            }
                            for e in result.evidences
                        ],
                    }
                )
                return result

        return execute
