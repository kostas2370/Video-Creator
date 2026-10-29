from rest_framework.routers import DefaultRouter

from .views import VideoSeriesView

router = DefaultRouter()
router.register("series", VideoSeriesView, basename="series")
urlpatterns = router.urls
