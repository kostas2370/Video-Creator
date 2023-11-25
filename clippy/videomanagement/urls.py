from .views import TemplatePromptView, TestView, VideoView
from rest_framework import routers
from django.urls import path
from .views import download_playlist
router = routers.DefaultRouter(trailing_slash = False)
router.register('templates/', TemplatePromptView)
router.register('test/', TestView)
router.register('video/', VideoView)
urlpatterns = router.urls

urlpatterns += [path('downloadplaylist/', download_playlist)]

