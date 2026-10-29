from rest_framework.routers import DefaultRouter

from .views import ClipProjectView

router = DefaultRouter()
router.register("clips", ClipProjectView, basename="clipproject")
