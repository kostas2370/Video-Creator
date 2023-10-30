from .views import TemplatePromptView
from rest_framework import routers

router = routers.DefaultRouter(trailing_slash = False)
router.register('templates/', TemplatePromptView)

urlpatterns = router.urls



