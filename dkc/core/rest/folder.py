from typing import Dict

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from guardian.utils import get_identity
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import Folder, Terms, TermsAgreement, Tree
from dkc.core.permissions import (
    HasAccess,
    IsAdmin,
    IsReadable,
    Permission,
    PermissionFilterBackend,
    PermissionGrant,
)

from .filtering import ActionSpecificFilterBackend, IntegerOrNullFilter
from .utils import FullCleanModelSerializer


class FolderSerializer(FullCleanModelSerializer):
    public: bool = serializers.BooleanField(read_only=True)
    access: Dict[str, bool] = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        fields = [
            'id',
            'name',
            'description',
            'parent',
            'created',
            'modified',
            'size',
            'public',
            'access',
        ]

    def get_access(self, folder: Folder) -> Dict[str, bool]:
        return folder.tree.get_access(self.context.get('user'))


class FolderUpdateSerializer(FolderSerializer):
    class Meta(FolderSerializer.Meta):
        fields = ['id', 'name', 'description']


class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terms
        fields = ['text', 'checksum']


class PostTermsAgreementSerializer(serializers.Serializer):
    checksum = serializers.CharField(required=True)


class FoldersFilterSet(filters.FilterSet):
    parent = IntegerOrNullFilter(required=True)


class FolderPermissionGrantSerializer(serializers.Serializer):
    name = serializers.CharField(required=True)
    model = serializers.ChoiceField(['user', 'group'], required=True)
    permission = serializers.ChoiceField([p.name for p in Permission], required=True)

    def _load_user_or_group(self, data):
        if isinstance(data, PermissionGrant):
            return data.user_or_group

        model = data.get('model')
        name = data.get('name')
        if model == 'user':
            return User.objects.filter(username=name).first()
        return Group.objects.filter(name=name).first()

    def to_representation(self, instance):
        user, group = get_identity(instance.user_or_group)
        if user:
            model = 'user'
            name = user.username
        else:
            model = 'group'
            name = group.name
        return {
            'name': name,
            'model': model,
            'permission': instance.permission.name,
        }

    def to_internal_value(self, data):
        return PermissionGrant(
            user_or_group=self._load_user_or_group(data),
            permission=Permission[data['permission']],
        )

    def validate(self, data):
        user_or_group = self._load_user_or_group(data)
        if user_or_group is None:
            raise serializers.ValidationError('Invalid user or group name')
        return data


class FolderPublicSerializer(serializers.Serializer):
    public = serializers.BooleanField()


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.all()

    permission_classes = [HasAccess]

    filter_backends = [PermissionFilterBackend, ActionSpecificFilterBackend]
    filterset_class = FoldersFilterSet

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return FolderUpdateSerializer
        return FolderSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['user'] = self.request.user
        return context

    # Atomically roll back the tree creation if folder creation fails
    @transaction.atomic
    def perform_create(self, serializer: serializers.ModelSerializer):
        parent: Folder = serializer.validated_data.get('parent')
        if parent:
            tree = parent.tree
            if not tree.has_permission(serializer.context['user'], permission=Permission.write):
                raise PermissionDenied()
        else:
            tree = Tree.objects.create()
            tree.grant_permission(
                PermissionGrant(
                    user_or_group=serializer.context['user'], permission=Permission.admin
                )
            )
        serializer.save(tree=tree)

    @swagger_auto_schema(
        operation_description='Retrieve the path from the root folder to the requested folder.',
        responses={200: FolderSerializer(many=True)},
    )
    @action(detail=True)
    def path(self, request, pk=None):
        folder = self.get_object()
        # Start with the root folder
        ancestors = folder.ancestors[::-1]
        serializer = self.get_serializer(ancestors, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Retrieve the terms of use for a folder.',
        responses={
            200: TermsSerializer,
            204: 'No terms of use exist for the folder.',
        },
    )
    @action(detail=True)
    def terms(self, request, pk=None):
        folder = self.get_object()
        try:
            terms = folder.tree.terms
        except Terms.DoesNotExist:
            return Response(status=204)

        serializer = TermsSerializer(terms)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Retrieve terms of use if your user must agree to them.',
        responses={
            200: TermsSerializer,
            204: 'No action is required; there are no terms, or you have already agreed.',
        },
    )
    @action(
        methods=['GET'], detail=True, url_path='terms/agreement', permission_classes=[IsReadable]
    )
    def terms_agreement(self, request, pk=None):
        folder = self.get_object()
        try:
            terms = folder.tree.terms
        except Terms.DoesNotExist:
            return Response(status=204)  # No terms for the folder

        user = request.user

        if not request.user.is_anonymous:
            try:
                TermsAgreement.objects.get(terms=terms, user=user, checksum=terms.checksum)
            except TermsAgreement.DoesNotExist:
                pass
            else:
                return Response(status=204)  # User has already agreed

        serializer = TermsSerializer(terms)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Agree to the terms of use for a folder.',
        request_body=PostTermsAgreementSerializer,
        responses={
            204: 'Your agreement was recorded.',
        },
    )
    @terms_agreement.mapping.post
    def agree_terms(self, request, pk=None):
        serializer = PostTermsAgreementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        checksum = serializer.validated_data['checksum']

        folder = self.get_object()
        try:
            terms = folder.tree.terms
        except Terms.DoesNotExist:
            raise ValidationError({'folder': 'This folder has no associated terms of use.'})

        if terms.checksum != checksum:
            raise ValidationError(
                {'checksum': 'Mismatched checksum. Your terms may be out of date.'}
            )

        TermsAgreement.objects.update_or_create(
            terms=terms, user=request.user, defaults={'checksum': checksum}
        )
        return Response(status=204)

    @swagger_auto_schema(
        operation_description='Get all user or group permissions set on a folder',
        responses={200: FolderPermissionGrantSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], permission_classes=[IsAdmin])
    def permissions(self, request, pk=None):
        tree: Tree = self.get_object().tree
        grants = tree.list_granted_permissions()
        serializer = FolderPermissionGrantSerializer(grants, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description=(
            'Set user or group permissions on a folder, '
            'removing any permissions not explicitly passed.'
        ),
        responses={200: FolderPermissionGrantSerializer(many=True)},
        request_body=FolderPermissionGrantSerializer(many=True),
    )
    @permissions.mapping.put
    def set_permission(self, request, pk=None):
        tree: Tree = self.get_object().tree
        serializer = FolderPermissionGrantSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        grants = serializer.validated_data
        tree.set_permission_list(grants)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Set user or group permissions on a folder',
        responses={200: FolderPermissionGrantSerializer(many=True)},
        request_body=FolderPermissionGrantSerializer(many=True),
    )
    @permissions.mapping.patch
    def patch_permission(self, request, pk=None):
        tree: Tree = self.get_object().tree
        serializer = FolderPermissionGrantSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        grants = serializer.validated_data
        tree.grant_permission_list(grants)

        grants = tree.list_granted_permissions()
        serializer = FolderPermissionGrantSerializer(grants, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Remove user or group permissions on a folder',
        responses={200: FolderPermissionGrantSerializer(many=True)},
        request_body=FolderPermissionGrantSerializer(many=True),
    )
    @permissions.mapping.delete
    def delete_permission(self, request, pk=None):
        tree: Tree = self.get_object().tree
        serializer = FolderPermissionGrantSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        grants = serializer.validated_data
        tree.remove_permission_list(grants)

        grants = tree.list_granted_permissions()
        serializer = FolderPermissionGrantSerializer(grants, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Set the public access flag',
        responses={200: FolderPublicSerializer},
        request_body=FolderPublicSerializer,
    )
    @action(detail=True, methods=['put'], permission_classes=[IsAdmin])
    def public(self, request, pk=None):
        tree: Tree = self.get_object().tree
        serializer = FolderPublicSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tree.public = serializer.validated_data['public']
        tree.save()
        return Response(serializer.data, status=200)
