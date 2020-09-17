from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from dkc.core.models import File

from .filtering import ActionSpecificFilterBackend


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = [
            'id',
            'name',
            'description',
            'content_type',
            'created',
            'modified',
            'owner',
            'sha512',
            'size',
        ]


class FileViewSet(ReadOnlyModelViewSet):
    queryset = File.objects.all()

    permission_classes = [
        AllowAny
        # IsAuthenticatedOrReadOnly
    ]
    serializer_class = FileSerializer

    filter_backends = [ActionSpecificFilterBackend]
    filterset_fields = ['folder', 'sha512']

    # TODO figure out how to indicate this response type in the OpenAPI schema
    @action(detail=True)
    def download(self, request, pk=None):
        file = get_object_or_404(File, pk=pk)
        return HttpResponseRedirect(file.blob.url)
