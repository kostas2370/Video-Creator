from .views.general_views import (
    IntroView,
    OutroView,
    AvatarView,
    VoiceView,
    SceneImageView,
)
from .views.generate_view import GenerateView
from .views.scene_view import SceneView
from .views.video_view import VideoView
from .views.twitch_views import generate_twitch

from rest_framework import routers
from django.urls import path

router = routers.DefaultRouter()


router.register("generate", GenerateView)
router.register("video", VideoView)
router.register("avatars", AvatarView)
router.register("voices", VoiceView)
router.register("scene", SceneView)
router.register("scene_image", SceneImageView)
router.register("intro", IntroView)
router.register("outro", OutroView)


urlpatterns = [
    path("twitch_generate/", generate_twitch),
]


urlpatterns += router.urls
