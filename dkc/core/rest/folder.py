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
        fields = ['id', 'name', 'description', 'parent', 'created', 'modified', 'size']


class FolderUpdateSerializer(FolderSerializer):
    class Meta(FolderSerializer.Meta):
        fields = ['id', 'name', 'description']


class FoldersFilterSet(filters.FilterSet):
    parent = IntegerOrNullFilter(required=True)


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.all()

    permission_classes = [
        AllowAny,
        # IsAuthenticatedOrReadOnly,
    ]

    filter_backends = [ActionSpecificFilterBackend]
    filterset_class = FoldersFilterSet

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return FolderUpdateSerializer
        return FolderSerializer

    @action(detail=True)
    def path(self, request, pk=None):
        folder = self.get_object()
        # Start with the root folder
        ancestors = folder.ancestors[::-1]
        serializer = self.get_serializer(ancestors, many=True)
        return Response(serializer.data)
