"""Opt-in, context-local timings. Never accept prompts, arguments or resource IDs."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from functools import wraps
from time import perf_counter
from uuid import uuid4


OPERATIONS = frozenset(
    {
        "open_document",
        "load_all_chunks",
        "bm25_build",
        "embedding",
        "retrieval",
        "tool_round",
        "provider_generation",
        "ingestion",
        "pdf_parse",
    }
)


@dataclass(frozen=True)
class Timing:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation: str
    duration_ms: float
    status: str

    def to_dict(self):
        return asdict(self)


_sink: ContextVar[Callable[[Timing], None] | None] = ContextVar("timing_sink", default=None)
_trace: ContextVar[str | None] = ContextVar("timing_trace", default=None)
_parent: ContextVar[str | None] = ContextVar("timing_parent", default=None)


@contextmanager
def capture_timings(sink: Callable[[Timing], None]) -> Iterator[str]:
    """One internally generated correlation ID per explicit request/profile scope."""
    trace_id = uuid4().hex
    tokens = (_sink.set(sink), _trace.set(trace_id), _parent.set(None))
    try:
        yield trace_id
    finally:
        _parent.reset(tokens[2])
        _trace.reset(tokens[1])
        _sink.reset(tokens[0])


@contextmanager
def timing(operation: str):
    if operation not in OPERATIONS:
        raise ValueError("Unknown timing operation")
    sink = _sink.get()
    if sink is None:
        yield
        return
    parent = _parent.get()
    span_id = uuid4().hex
    token = _parent.set(span_id)
    started, status = perf_counter(), "ok"
    try:
        yield
    except BaseException:
        status = "error"
        raise
    finally:
        elapsed = (perf_counter() - started) * 1000
        _parent.reset(token)
        try:
            sink(Timing(_trace.get(), span_id, parent, operation, elapsed, status))
        except Exception:
            # Diagnostics must not change learning behavior or mask the original failure.
            pass


def timed(operation: str):
    if operation not in OPERATIONS:
        raise ValueError("Unknown timing operation")

    def decorate(function):
        @wraps(function)
        def measured(*args, **kwargs):
            with timing(operation):
                return function(*args, **kwargs)

        return measured

    return decorate
