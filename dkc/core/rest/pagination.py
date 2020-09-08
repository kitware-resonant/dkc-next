from rest_framework.pagination import LimitOffsetPagination


class BoundedLimitOffsetPagination(LimitOffsetPagination):
    """
    Application specific pagination subclass.

    This simply overrides the `max_limit` value from the parent to set an
    upper bound on the page size that can be returned to the user.
    """

    default_limit = 100
    max_limit = 1000
