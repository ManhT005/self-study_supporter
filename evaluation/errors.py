from evaluation.schema import ErrorCode
from study_supporter.domain.errors import EvidenceNotFound, QuotaExceeded
from study_supporter.domain.provider_errors import ProviderAuthenticationError, ProviderUnavailable


class EvaluationFailure(RuntimeError):
    def __init__(self, code: ErrorCode):
        self.code = code
        super().__init__(code)


def error_code(exc: Exception) -> ErrorCode:
    if isinstance(exc, EvaluationFailure):
        return exc.code
    if isinstance(exc, EvidenceNotFound):
        return "NO_EVIDENCE"
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, (ProviderUnavailable, ProviderAuthenticationError, QuotaExceeded)):
        return "PROVIDER_ERROR"
    if isinstance(exc, ValueError):
        return "INVALID_SCHEMA"
    return "INTERNAL"
