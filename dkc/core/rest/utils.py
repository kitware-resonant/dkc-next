class FormattableDict(dict):
    """
    A dict with a no-op .format method.

    This is useful to pass into DRF, as the `message` of an eventual `ValidationError`.
    """

    def format(self, *args, **kwargs):
        return self
