from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import Folder


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'description', 'parent']


class IntegerOrNullFilter(filters.Filter):
    """
    Supports filtering by either an integer or null.

    This allows clients to use a special value of "null" to filter for null values,
    otherwise it parses the value to an integer.
    """

    def filter(self, qs, value: str):
        if value == 'null':
            return qs.filter(**{self.field_name + '__isnull': True})
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError(
                {
                    self.field_name: ['May only be an integer or "null".'],
                }
            )

        return qs.filter(**{self.field_name: value})


class FoldersFilterSet(filters.FilterSet):
    parent = IntegerOrNullFilter(required=True)


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.all()

    permission_classes = [
        AllowAny,
        # IsAuthenticatedOrReadOnly,
    ]
    serializer_class = FolderSerializer

    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = FoldersFilterSet

    def filter_queryset(self, queryset):
        # Only apply the filterset class on the list endpoint
        if self.action != 'list':
            self.filterset_class = None
        return super().filter_queryset(queryset)

    @action(detail=True)
    def path(self, request, pk=None):
        folder = self.get_object()
        serializer = self.get_serializer(folder.path_to_root(), many=True)
        return Response(serializer.data)
