class DocumentUnsupported(ValueError):
    """Document is invalid, too large or has no usable text layer."""


class EvidenceNotFound(LookupError):
    """Missing document or evidence, including an ownership mismatch."""


class EmbeddingUnavailable(RuntimeError):
    """Embedding provider cannot produce usable vectors."""


class QuotaExceeded(RuntimeError):
    """A provider has exhausted its quota."""
