from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import Folder

from .filtering import ActionSpecificFilterBackend, IntegerOrNullFilter


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'description', 'parent']


class FoldersFilterSet(filters.FilterSet):
    parent = IntegerOrNullFilter(required=True)


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.all()

    permission_classes = [
        AllowAny,
        # IsAuthenticatedOrReadOnly,
    ]
    serializer_class = FolderSerializer

    filter_backends = [ActionSpecificFilterBackend]
    filterset_class = FoldersFilterSet

    @action(detail=True)
    def path(self, request, pk=None):
        folder = self.get_object()
        serializer = self.get_serializer(folder.path_to_root(), many=True)
        return Response(serializer.data)
