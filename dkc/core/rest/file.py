from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.exceptions import QuotaLimitedError
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
            'description',
            'size',
            'content_type',
            'sha512',
            'folder',
            'creator',
            'created',
            'modified',
        ]
        read_only_fields = [
            'creator',
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


class FileUpdateSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        fields = FileSerializer.Meta.fields + ['blob']
        read_only_fields = FileSerializer.Meta.read_only_fields + ['folder', 'size']


class FileViewSet(ModelViewSet):
    queryset = File.objects.all()

    permission_classes = [HasAccess]

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return FileUpdateSerializer
        return FileSerializer

    def perform_create(self, serializer: FileSerializer):
        folder: Folder = serializer.validated_data['folder']
        user: User = self.request.user
        if not folder.has_permission(user, permission=Permission.write):
            raise PermissionDenied()
        try:
            serializer.save(creator=user)
        except QuotaLimitedError:
            raise serializers.ValidationError(
                {'size': ['This file would exceed the size quota for this folder.']}
            )

    @swagger_auto_schema(
        responses={
            204: 'This file is pending or has no associated content.',
            302: 'You will be redirected to download the file contents.',
        },
    )
    @action(detail=True)
    def download(self, request, pk=None):
        """Download a file."""
        file = get_object_or_404(File, pk=pk)
        if file.blob:  # FieldFiles are falsy when not populated with a file
            return HttpResponseRedirect(file.blob.url)
        return Response(status=204)
