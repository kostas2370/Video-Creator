from django.urls import path
from rest_framework.routers import DefaultRouter

from .events import project_events
from .views import ClipProjectView

router = DefaultRouter()
router.register("clips", ClipProjectView, basename="clipproject")

urlpatterns = [
    path("clips/<uuid:project_id>/events/", project_events, name="clipproject-events")
]
