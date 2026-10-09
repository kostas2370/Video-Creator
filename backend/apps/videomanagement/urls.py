from .views.general_views import (
    IntroView,
    OutroView,
    AvatarView,
    VoiceView,
    SceneImageView,
    TemplatePromptView,
)
from .event_stream import event_updates
from .views.generate_view import GenerateView
from .views.scene_view import SceneView
from .views.video_view import VideoView

from rest_framework import routers
from django.urls import path

router = routers.DefaultRouter()


router.register("videos", VideoView)
router.register("avatars", AvatarView)
router.register("voices", VoiceView)
router.register("scenes", SceneView)
router.register("scene_images", SceneImageView)
router.register("intros", IntroView)
router.register("outros", OutroView)
router.register("templates", TemplatePromptView)


urlpatterns = [
    path("videos/<uuid:video_id>/events/", event_updates, name="video_events"),
    path("generate/", GenerateView.as_view(), name="generate"),
]


urlpatterns += router.urls
