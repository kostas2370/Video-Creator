from .views import TemplatePromptView, TestView, VideoView, AvatarView, VoiceView
from rest_framework import routers
from django.urls import path
from .views import download_playlist, render_video
router = routers.DefaultRouter(trailing_slash = False)
router.register('templates/', TemplatePromptView)
router.register('test/', TestView)
router.register('video/', VideoView)
router.register('avatars/', AvatarView)
router.register('voices/', VoiceView)


urlpatterns = router.urls

urlpatterns += [path('downloadplaylist/', download_playlist),
                path('render/', render_video)
                ]


