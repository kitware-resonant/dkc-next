from django.core.exceptions import ValidationError


class QuotaLimitedError(ValidationError):
    """Raised when a quota would be exceeded by an increment operation."""

    def __init__(self, message='Root folder size quota would be exceeded.', *args, **kwargs):
        super().__init__(message, *args, **kwargs)
