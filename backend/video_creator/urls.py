from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions, routers

from apps.clips.urls import router as clips_router
from apps.clips.protected_media import public_clip_media
from apps.series.urls import router as series_router
from apps.videomanagement.urls import router as video_router


api_router = routers.DefaultRouter()
api_router.registry = video_router.registry + series_router.registry + clips_router.registry

schema_view = get_schema_view(
    openapi.Info(
        title="Viddie API",
        default_version="v1",
        description="Here you can see all the apis",
        contact=openapi.Contact(email="kodamia@cs.ihu.gr"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path(
        "swagger<format>/", schema_view.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("admin/", admin.site.urls),
    path("api/", include("apps.usermanagement.urls")),
    path("api/", include("apps.apikeysmanagement.urls")),
    path("api/", include("apps.videomanagement.urls")),
    path("api/", include("apps.clips.urls")),
    path("api/", include(api_router.urls)),
    path("media/clips/<path:path>", public_clip_media),
    path("api/news/", include("apps.news.urls")),
    path("api/publishing/", include("apps.publishing.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Stored file names already start with media/. Never expose BASE_DIR through
    # an empty URL prefix: that would also serve .env, the database, and source.
    urlpatterns += static("/media/", document_root=settings.BASE_DIR / "media")
