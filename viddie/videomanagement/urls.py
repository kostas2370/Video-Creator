from .views import TemplatePromptView, GenerateView, VideoView, AvatarView, VoiceView, SceneView, SceneImageView,\
    change_image_scene, generate_twitch
from rest_framework import routers
from django.urls import path
from .views import download_playlist, render_video, video_regenerate
router = routers.DefaultRouter()
router.register('templates', TemplatePromptView)
router.register('generate', GenerateView)
router.register('video', VideoView)
router.register('avatars', AvatarView)
router.register('voices', VoiceView)
router.register('scene', SceneView)
router.register('scene_image', SceneImageView)

urlpatterns = [path('downloadplaylist/', download_playlist),
               path('render/', render_video),
               path('change_image/', change_image_scene),
               path('regenerate/', video_regenerate),
               path('twitch_generate/', generate_twitch)
               ]


urlpatterns += router.urls
