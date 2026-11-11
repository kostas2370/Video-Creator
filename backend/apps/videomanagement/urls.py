from django.urls import path
from rest_framework import routers

from apps.videomanagement.views.assets import (
    AvatarView,
    IntroView,
    OutroView,
    SceneImageView,
    TemplatePromptView,
    VoiceView,
)
from apps.videomanagement.views.generation import GenerateView, GenerationModelsView
from apps.videomanagement.views.scenes import SceneView
from apps.videomanagement.views.videos import VideoView

from .event_stream import event_updates
from .views.captions import CaptionProjectView
from .views.draft_jobs import DraftJobView
from .views.icons import IconDetailView, IconListView
from .views.library import MediaAssetView
from .views.music_catalog import MusicCatalogView

router = routers.DefaultRouter()


router.register("media-assets", MediaAssetView)
router.register("music-catalog", MusicCatalogView)
router.register("videos", VideoView)
router.register("captions", CaptionProjectView)
router.register("avatars", AvatarView)
router.register("voices", VoiceView)
router.register("scenes", SceneView)
router.register("scene_images", SceneImageView)
router.register("intros", IntroView)
router.register("outros", OutroView)
router.register("templates", TemplatePromptView)


urlpatterns = [
    path("draft-jobs/", DraftJobView.as_view(), name="draft-job"),
    path("icons/", IconListView.as_view(), name="icons"),
    path("icons/<str:pk>/", IconDetailView.as_view(), name="icon-detail"),
    path(
        "generation-models/", GenerationModelsView.as_view(), name="generation_models"
    ),
    path("videos/<uuid:video_id>/events/", event_updates, name="video_events"),
    path("generate/", GenerateView.as_view(), name="generate"),
]
