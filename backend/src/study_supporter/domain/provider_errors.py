class ProviderAuthenticationError(RuntimeError):
    """Provider credential or authorization failure; do not hide with fallback."""


class ProviderUnavailable(RuntimeError):
    """A transient provider failure, safe for fallback."""
