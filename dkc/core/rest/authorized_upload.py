from datetime import timedelta

from django.conf import settings
from django.core.signing import Signer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import View
from rest_framework.viewsets import GenericViewSet

from dkc.core.models import AuthorizedUpload, Folder
from dkc.core.permissions import Permission


class AuthorizedUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorizedUpload
        fields = ['id', 'created', 'creator', 'expires', 'folder', 'signature']

    signature: str = serializers.SerializerMethodField()

    def get_signature(self, upload: AuthorizedUpload) -> str:
        return Signer().sign(str(upload.id))


class CreateAuthorizedUploadSerializer(serializers.Serializer):
    folder = serializers.IntegerField()


class CanDeleteAuthorization(BasePermission):
    message = 'Only the creator of an authorized upload may delete it.'

    def has_object_permission(self, request: Request, view: View, obj: AuthorizedUpload) -> bool:
        return view.action != 'destroy' or request.user.is_superuser or request.user == obj.creator

    def has_permission(self, request: Request, view: View) -> bool:
        return True


class AuthorizedUploadViewSet(mixins.DestroyModelMixin, GenericViewSet):
    queryset = AuthorizedUpload.objects.all()

    permission_classes = [CanDeleteAuthorization]
    serializer_class = AuthorizedUploadSerializer

    @swagger_auto_schema(
        responses={201: AuthorizedUploadSerializer},
        request_body=CreateAuthorizedUploadSerializer,
    )
    def create(self, request, pk=None):
        """Authorize an upload to a folder on your behalf."""
        serializer = CreateAuthorizedUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder = get_object_or_404(Folder, pk=serializer.validated_data['folder'])

        if not folder.has_permission(request.user, Permission.write):
            raise PermissionDenied('You are not allowed to create files in this folder.')

        expires = timezone.now() + timedelta(days=settings.DKC_AUTHORIZED_UPLOAD_EXPIRATION_DAYS)
        upload = AuthorizedUpload.objects.create(
            folder=folder, creator=request.user, expires=expires
        )
        serializer = AuthorizedUploadSerializer(upload)
        return Response(serializer.data, status=201)
