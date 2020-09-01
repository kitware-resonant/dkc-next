from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from dkc.core.models import Folder


class FolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        fields = ['id', 'name', 'description', 'parent']


class FolderViewSet(ModelViewSet):
    queryset = Folder.objects.all()

    permission_classes = [
        AllowAny,
        # IsAuthenticatedOrReadOnly,
    ]
    serializer_class = FolderSerializer

    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ['parent_id']

    @action(methods=['get'], detail=False)
    def roots(self, request):
        queryset = Folder.objects.filter(parent_id__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
