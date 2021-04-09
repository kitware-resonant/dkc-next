from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers

from dkc.core import views
from dkc.core.rest import AuthorizedUploadViewSet, FileViewSet, FolderViewSet, UserViewSet

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'authorized_uploads', AuthorizedUploadViewSet)
router.register(r'files', FileViewSet)
router.register(r'folders', FolderViewSet)
router.register(r'users', UserViewSet)

# OpenAPI generation
schema_view = get_schema_view(
    openapi.Info(title='data.kitware.com', default_version='v1', description=''),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', RedirectView.as_view(url=settings.DKC_SPA_URL, permanent=True), name='home'),
    path('accounts/', include('allauth.urls')),
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('admin/', admin.site.urls),
    path('staff/', views.staff_home, name='staff-home'),
    path('staff/tree/', views.staff_tree_list, name='staff-tree-list'),
    path('api/v2/s3-upload/', include('s3_file_field.urls')),
    path('api/v2/', include(router.urls)),
    path('api/docs/redoc/', schema_view.with_ui('redoc'), name='docs-redoc'),
    path('api/docs/swagger/', schema_view.with_ui('swagger'), name='docs-swagger'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
