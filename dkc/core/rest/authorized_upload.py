import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, serializers
from rest_framework.decorators import action
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


class CreateAuthorizedUploadSerializer(serializers.Serializer):
    folder = serializers.IntegerField()


class CompleteAuthorizedUploadSerializer(serializers.Serializer):
    authorization = serializers.CharField()


class CanDeleteAuthorization(BasePermission):
    message = 'Only the creator of an authorized upload may delete it.'

    def has_object_permission(self, request: Request, view: View, obj: AuthorizedUpload) -> bool:
        return view.action != 'destroy' or request.user.is_superuser or request.user == obj.creator


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

        upload = AuthorizedUpload.objects.create(folder=folder, creator=request.user)
        serializer = AuthorizedUploadSerializer(upload)
        return Response(serializer.data, status=201)

    @swagger_auto_schema(
        responses={204: 'The authorized upload was finalized.'},
        request_body=CompleteAuthorizedUploadSerializer,
    )
    @action(
        detail=True, methods=['post'], queryset=AuthorizedUpload.objects.select_related('folder')
    )
    def completion(self, request, pk=None):
        """Mark an authorized upload as complete and notify its originator."""
        serializer = CompleteAuthorizedUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        upload = self.get_object()

        try:
            upload.verify_signature(serializer.validated_data['authorization'])
        except signing.BadSignature:
            logger = logging.getLogger('django.security.SuspiciousOperation')
            logger.warning('Authorized upload signature tampering detected.')
            raise PermissionDenied('Invalid authorization signature.')

        context = {
            'folder': upload.folder,
            'folder_url': f'{settings.DKC_SPA_URL}#/folders/{upload.folder.id}',
        }

        send_mail(
            subject='Authorized upload complete',
            message=render_to_string('email/authorized_upload_complete.txt', context),
            html_message=render_to_string('email/authorized_upload_complete.html', context),
            from_email=None,
            recipient_list=[upload.creator.email],
        )

        upload.delete()
        return Response(status=204)
