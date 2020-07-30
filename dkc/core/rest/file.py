from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from dkc.core.models import File
from dkc.core.rest.user import UserSerializer
from dkc.core.tasks import file_compute_checksum


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'name', 'checksum', 'created', 'owner']
        read_only_fields = ['checksum', 'created']

    owner = UserSerializer()


class FileViewSet(ReadOnlyModelViewSet):
    queryset = File.objects.all()

    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = FileSerializer

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['name', 'checksum']

    pagination_class = PageNumberPagination

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        file = get_object_or_404(File, pk=pk)
        return HttpResponseRedirect(file.blob.url)

    @action(detail=True, methods=['post'])
    def compute(self, request, pk=None):
        # Ensure that the file exists, so a non-existent pk isn't dispatched
        file = get_object_or_404(File, pk=pk)
        file_compute_checksum.delay(file.pk)
        return Response('', status=status.HTTP_202_ACCEPTED)
