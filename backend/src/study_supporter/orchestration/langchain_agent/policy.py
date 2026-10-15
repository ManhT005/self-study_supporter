import time
from dataclasses import dataclass


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
