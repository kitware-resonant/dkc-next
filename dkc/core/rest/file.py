import logging
from typing import Dict

from django.contrib.auth.models import User
from django.core import signing
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import View
from rest_framework.viewsets import ModelViewSet

from dkc.core.exceptions import QuotaLimitedError
from dkc.core.models import AuthorizedUpload, File, Folder
from dkc.core.permissions import HasAccess, Permission, PermissionFilterBackend

from .filtering import ActionSpecificFilterBackend
from .utils import FormattableDict


class FileSerializer(serializers.ModelSerializer):
    access: Dict[str, bool] = serializers.SerializerMethodField()

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
            'user_metadata',
            'access',
            'public',
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

    def get_access(self, file: File) -> Dict[str, bool]:
        return file.folder.tree.get_access(self.context.get('user'))

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


class HashDownloadSerializer(serializers.Serializer):
    sha512 = serializers.CharField(min_length=128, max_length=128)


class CreateWithAuthorizedUpload(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        return False

    def has_permission(self, request: Request, view: View) -> bool:
        # This doesn't actually do the policy enforcement, it simply allows requests
        # through if they are authorized upload requests. Enforcement is done in the
        # view's `perform_create` method.
        return view.action == 'create' and 'authorization' in request.data


class FileViewSet(ModelViewSet):
    # The tree is required for 'access' and 'public' serializer fields
    queryset = File.objects.select_related('folder__tree')

    permission_classes = [HasAccess | CreateWithAuthorizedUpload]

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return FileUpdateSerializer
        return FileSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context

    def _validate_authorized_upload(self, authorization: str, folder: Folder) -> User:
        try:
            signed_obj = signing.loads(authorization)
        except signing.BadSignature:
            logger = logging.getLogger('django.security.SuspiciousOperation')
            logger.warning('Authorized upload signature tampering detected.')
            raise PermissionDenied('Invalid authorization signature.')

        if signed_obj.get('scope') != 'authorized_upload':
            raise PermissionDenied('Invalid signature scope.')

        try:
            upload: AuthorizedUpload = AuthorizedUpload.objects.select_related('creator').get(
                pk=signed_obj['id']
            )
        except AuthorizedUpload.DoesNotExist:
            raise PermissionDenied('This upload authorization has been revoked.')

        if upload.expires < timezone.now():
            raise PermissionDenied(
                'This upload authorization has expired. Please request a new link.'
            )
        if upload.folder.id != folder.id:
            raise PermissionDenied('This upload was authorized to a different folder.')

        return upload.creator

    def perform_create(self, serializer: FileSerializer):
        folder: Folder = serializer.validated_data['folder']
        if 'authorization' in self.request.data:
            user = self._validate_authorized_upload(self.request.data['authorization'], folder)
        else:
            user: User = self.request.user

        if not folder.has_permission(user, permission=Permission.write):
            raise PermissionDenied('You are not allowed to create files in this folder.')
        try:
            serializer.save(creator=user)
        except QuotaLimitedError:
            raise serializers.ValidationError(
                {'size': ['This file would exceed the size quota for this folder.']}
            )

    @swagger_auto_schema(
        responses={
            204: 'This file is pending and has no associated content.',
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

    @swagger_auto_schema(
        query_serializer=HashDownloadSerializer,
        responses={
            200: None,  # needed to override default
            302: 'You will be redirected to download the file contents.',
            404: 'No file exists with the given hash.',
        },
    )
    @action(detail=False, filterset_fields=[], pagination_class=None)
    def hash_download(self, request):
        """Download a file based on the hash of its contents."""
        serializer = HashDownloadSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        sha512 = serializer.validated_data['sha512'].lower()
        qs = File.objects.filter(sha512=sha512).only('blob').order_by()
        qs = File.filter_by_permission(request.user, Permission.read, qs)

        file = qs.first()
        if not file:
            return Response(status=404)

        return HttpResponseRedirect(file.blob.url)
