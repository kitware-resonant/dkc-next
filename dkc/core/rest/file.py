from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import File, Folder
from dkc.core.permissions import HasAccess, Permission, PermissionFilterBackend

from .filtering import ActionSpecificFilterBackend
from .utils import FormattableDict


class FileSerializer(serializers.ModelSerializer):
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
        # ModelSerializer cannot auto-generate validators for model-level constraints
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=File.objects.all(),
                fields=['folder', 'name'],
                message=FormattableDict({'name': 'A file with that name already exists here.'}),
            ),
        ]

    def validate(self, attrs):
        self._validate_unique_folder_siblings(attrs)
        return attrs

    def _validate_unique_folder_siblings(self, attrs):
        if self.instance is None:
            # Create
            # By this point, other validators will have run, ensuring that 'name' and 'folder' exist
            name = attrs['name']
            folder_id = attrs['folder']
        else:
            # Update
            # On a partial update, 'name' and 'folder' might be absent, so use the existing instance
            name = attrs['name'] if 'name' in attrs else self.instance.name
            folder_id = attrs['folder'] if 'folder' in attrs else self.instance.folder_id
        if Folder.objects.filter(name=name, parent_id=folder_id).exists():
            raise serializers.ValidationError(
                {'name': 'A folder with that name already exists here.'}, code='unique'
            )


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()

    permission_classes = [HasAccess]
    serializer_class = FileSerializer

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    def perform_create(self, serializer: FileSerializer):
        folder: Folder = serializer.validated_data.get('folder')
        if not folder.has_permission(self.request.user, permission=Permission.write):
            raise PermissionDenied()
        serializer.save()

    # TODO figure out how to indicate this response type in the OpenAPI schema
    @action(detail=True)
    def download(self, request, pk=None):
        file = get_object_or_404(File, pk=pk)
        return HttpResponseRedirect(file.blob.url)
