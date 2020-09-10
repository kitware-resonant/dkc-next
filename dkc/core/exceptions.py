from django.core.exceptions import ValidationError


class MaxFolderDepthExceeded(ValidationError):
    def __init__(self, message=None, *args, **kwargs):
        super().__init__(message or 'Maximum folder tree depth exceeded.', *args, **kwargs)
