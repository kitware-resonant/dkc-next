from django_filters import rest_framework as filters
from rest_framework import serializers


class ActionSpecificFilterBackend(filters.DjangoFilterBackend):
    """
    Use this filter backend to only apply filters to certain actions.

    By default, filtering is only applied to the 'list' action. A custom set of
    actions to which the view's filters should be applied can be specified as a
    list via the `filtered_actions` attribute of the view.
    """

    def filter_queryset(self, request, queryset, view):
        filtered_actions = getattr(view, 'filtered_actions', ['list'])
        if view.action in filtered_actions:
            return super().filter_queryset(request, queryset, view)
        return queryset


class IntegerOrNullFilter(filters.Filter):
    """
    Supports filtering by either an integer or null.

    This allows clients to use a special value of "null" to filter for null values,
    otherwise it parses the value to an integer.
    """

    def filter(self, qs, value: str):
        if value == 'null':
            return qs.filter(**{f'{self.field_name}__isnull': True})
        try:
            value = int(value)
        except ValueError:
            raise serializers.ValidationError(
                {
                    self.field_name: ['May only be an integer or "null".'],
                }
            )

        return qs.filter(**{self.field_name: value})
