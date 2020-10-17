from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_yasg2 import openapi
from drf_yasg2.views import get_schema_view
from rest_framework import permissions, routers

from dkc.core.rest import FileViewSet, FolderViewSet

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'files', FileViewSet)
router.register(r'folders', FolderViewSet)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='data.kitware.com', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('api/v2/', include(router.urls)),
    path('api/docs/redoc', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger', schema_view.with_ui('swagger'), name='docs-swagger'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
