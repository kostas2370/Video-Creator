from pathlib import Path

from django.apps import apps
from django.urls import path
from django.views.decorators.http import require_safe
from django.views.static import serve

urlpatterns = [
    path(
        f"static/{directory}/<path:path>",
        require_safe(serve),
        {"document_root": Path(apps.get_app_config(app).path) / "static" / directory},
    )
    for app, directory in (("admin", "admin"), ("drf_yasg", "drf-yasg"))
]
