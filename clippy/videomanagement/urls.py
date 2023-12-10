from .views import TemplatePromptView, TestView, VideoView, AvatarView, VoiceView,SceneView
from rest_framework import routers
from django.urls import path
from .views import download_playlist, render_video, update_scene_view
router = routers.DefaultRouter()
router.register('templates', TemplatePromptView)
router.register('test', TestView)
router.register('video', VideoView)
router.register('avatars', AvatarView)
router.register('voices', VoiceView)
router.register('scene', SceneView)


urlpatterns = [path('downloadplaylist/', download_playlist),
               path('render/', render_video),
               path('update_scene/', update_scene_view)]

urlpatterns += router.urls
