from .views import TemplatePromptView, TestView
from rest_framework import routers
from django.urls import path
from .views import downloadPlaylist
router = routers.DefaultRouter(trailing_slash = False)
router.register('templates/', TemplatePromptView)
router.register('test/', TestView)
urlpatterns = router.urls

urlpatterns += [path('downloadplaylist/', downloadPlaylist)]

