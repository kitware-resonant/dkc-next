from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import File
from dkc.core.permissions import HasAccess, PermissionFilterBackend

from .filtering import ActionSpecificFilterBackend
from .utils import FullCleanModelSerializer


class FileSerializer(FullCleanModelSerializer):
    class Meta:
        model = File
        fields = [
            'id',
            'name',
            'blob',
            'folder',
            'description',
            'content_type',
            'created',
            'modified',
            'creator',
            'sha512',
            'size',
        ]


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()

    permission_classes = [HasAccess & IsAuthenticatedOrReadOnly]
    serializer_class = FileSerializer

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    # TODO figure out how to indicate this response type in the OpenAPI schema
    @action(detail=True)
    def download(self, request, pk=None):
        file = get_object_or_404(File, pk=pk)
        return HttpResponseRedirect(file.blob.url)
