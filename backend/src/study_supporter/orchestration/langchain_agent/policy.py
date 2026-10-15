import time
import hashlib
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class ExecutionPolicy:
    max_tool_actions: int = 5
    timeout_seconds: float = 45
    max_question_chars: int = 8000
    max_answer_chars: int = 16000
    snippet_chars: int = 1200

    def __post_init__(self):
        if not 1 <= self.max_tool_actions <= 20 or not 0 < self.timeout_seconds <= 45:
            raise ValueError("Invalid experimental execution budget")
        if min(self.max_question_chars, self.max_answer_chars, self.snippet_chars) < 1:
            raise ValueError("Invalid experimental output limit")


class BudgetExhausted(Exception):
    pass


class ExecutionBudget:
    def __init__(self, policy):
        self.policy = policy
        self.deadline = time.monotonic() + policy.timeout_seconds
        self.actions = 0
        self.model_calls = 0

    def check_time(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError

    def take_action(self):
        self.check_time()
        if self.actions >= self.policy.max_tool_actions:
            raise BudgetExhausted
        self.actions += 1

    def take_model_call(self):
        self.check_time()
        if self.model_calls >= self.policy.max_tool_actions + 1:
            raise BudgetExhausted
        self.model_calls += 1


class NoteWriteDenied(Exception):
    pass


class ConfirmedNoteWrite:
    """Server-issued approval, bound to exact scope, request and normalized note.

    Reuse this same object for retries of one operation. It reserves the write
    before IO, including uncertain failures; issuing a new object is a new approval.
    Never construct from model output or infer confirmation from question text.
    """

    def __init__(self, context, question, note, operation_id, *, confirmed=False):
        from study_supporter.orchestration.langchain_agent.models import SaveNoteInput

        validated = SaveNoteInput(note=note, operation_id=operation_id)
        if confirmed is not True or validated.operation_id is None:
            raise NoteWriteDenied
        self.context = context
        self.question_hash = hashlib.sha256(question.encode()).digest()
        self.note_hash = hashlib.sha256(validated.note.encode()).digest()
        self.operation_id = operation_id
        self.deadline = time.monotonic() + 300
        self._attempted = False
        self._saved = False
        self._lock = RLock()

    def save(self, notes, request, note, operation_id, budget):
        with self._lock:
            budget.check_time()
            if (
                notes is None
                or request.context != self.context
                or hashlib.sha256(request.question.encode()).digest() != self.question_hash
                or hashlib.sha256(note.encode()).digest() != self.note_hash
                or operation_id not in {None, self.operation_id}
                or time.monotonic() >= self.deadline
            ):
                raise NoteWriteDenied
            if self._attempted:
                return {"status": "already_saved" if self._saved else "write_not_retried"}
            self._attempted = True
            # Intentionally synchronous: a cancelled background task must never commit
            # a late write. The experiment only permits bounded fixture repositories.
            notes.execute(request.context, note)
            self._saved = True
            return {"status": "saved"}
