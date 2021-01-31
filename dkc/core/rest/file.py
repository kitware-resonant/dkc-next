from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import File, Folder
from dkc.core.permissions import HasAccess, Permission, PermissionFilterBackend

from .filtering import ActionSpecificFilterBackend
from .utils import FullCleanModelSerializer


class FileSerializer(FullCleanModelSerializer):
    class Meta:
        model = File
        fields = [
            'id',
            'name',
            'description',
            'size',
            'content_type',
            'blob',
            'sha512',
            'folder',
            'creator',
            'created',
            'modified',
        ]
        read_only_fields = [
            'creator',
        ]


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()

    permission_classes = [HasAccess]
    serializer_class = FileSerializer

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    def perform_create(self, serializer: FileSerializer):
        folder: Folder = serializer.validated_data['folder']
        user: User = self.request.user
        if not folder.has_permission(user, permission=Permission.write):
            raise PermissionDenied()
        serializer.save(creator=user)

    # TODO figure out how to indicate this response type in the OpenAPI schema
    @action(detail=True)
    def download(self, request, pk=None):
        file = get_object_or_404(File, pk=pk)
        return HttpResponseRedirect(file.blob.url)
