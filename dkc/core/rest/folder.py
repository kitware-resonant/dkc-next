from django.contrib.auth.models import User
from django.db import transaction
from django_filters import rest_framework as filters
from drf_yasg2.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import Folder, Terms, TermsAgreement, Tree

from .filtering import ActionSpecificFilterBackend, IntegerOrNullFilter


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'description', 'parent', 'created', 'modified', 'size']


class FolderUpdateSerializer(FolderSerializer):
    class Meta(FolderSerializer.Meta):
        fields = ['id', 'name', 'description']


class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terms
        fields = ['text', 'checksum']


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

    # Atomically roll back the tree creation if folder creation fails
    @transaction.atomic
    def perform_create(self, serializer: serializers.ModelSerializer):
        parent: Folder = serializer.validated_data.get('parent')
        tree = parent.tree if parent else Tree.objects.create()
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
    @action(detail=True, url_path='terms/agreement')
    def terms_agreement(self, request, pk=None):
        folder = self.get_object()
        try:
            terms = folder.tree.terms
        except Terms.DoesNotExist:
            return Response(status=204)  # No terms for the folder

        # TODO get the actual user once REST authentication is in place
        user = User.objects.first()

        # TODO if no user is authenticated, just send out the terms.

        try:
            agreement = TermsAgreement.objects.get(terms=terms, user=user)
            if agreement.checksum == terms.checksum:
                return Response(status=204)  # User has already agreed
        except TermsAgreement.DoesNotExist:
            ...
        serializer = TermsSerializer(terms)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description='Agree to the terms of use for a folder.',
        responses={
            204: 'Your agreement was recorded.',
        },
    )
    @action(
        methods=['POST'],
        serializer_class=None,
        detail=True,
        url_path=r'terms/agreement/(?P<checksum>\w+)',
    )
    def agree_terms(self, request, checksum=None, pk=None):
        folder = self.get_object()
        try:
            terms = folder.tree.terms
        except Terms.DoesNotExist:
            raise ValidationError({'folder': 'This folder has no associated terms of use.'})

        if terms.checksum != checksum:
            raise ValidationError(
                {'checksum': 'Mismatched checksum. Your terms may be out of date.'}
            )

        # TODO get the actual user once REST authentication is in place
        user = User.objects.first()

        TermsAgreement.objects.update_or_create(
            terms=terms, user=user, defaults={'checksum': checksum}
        )
        return Response(status=204)
