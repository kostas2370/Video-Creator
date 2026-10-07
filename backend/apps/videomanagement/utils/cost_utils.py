import logging
from contextlib import contextmanager

from django.contrib.auth import get_user_model
from django.db.models import F
from rest_framework.exceptions import PermissionDenied

from ..models import SceneImage, VideoType

logger = logging.getLogger(__name__)


costs = {
    "scene_API": 0.02,
    "scene_LOCAL": 0.01,
    "scene_image_AI": 0.08,
    "scene_image_WEB": 0.04,
    "scene_image_DALL-E": 0.08,
}


@contextmanager
def reserve_scene_credit(user, cost, minimum_balance):
    """Reserve credit atomically before work, refunding failed operations."""
    accounts = get_user_model().objects.filter(pk=user.pk)
    if not user.is_superuser:
        accounts = accounts.filter(
            generation_limit_for_ai__gt=minimum_balance,
            generation_limit_for_ai__gte=cost,
        )
    if not accounts.update(generation_limit_for_ai=F("generation_limit_for_ai") - cost):
        raise PermissionDenied("You do not have enough tokens !")
    user.refresh_from_db(fields=["generation_limit_for_ai"])
    try:
        yield
    except Exception:
        get_user_model().objects.filter(pk=user.pk).update(
            generation_limit_for_ai=F("generation_limit_for_ai") + cost
        )
        user.refresh_from_db(fields=["generation_limit_for_ai"])
        raise


def calculate_total_cost(video):
    total_cost = 0
    scenes = video.scenes.all()
    scene_count = scenes.count()

    if video.video_type == VideoType.AI:
        voice_type = getattr(video.voice_model, "type", None)
        total_cost += 0.12 + scene_count * costs.get(f"scene_{voice_type}", 0)
        scene_images_count = (
            SceneImage.objects.filter(scene__in=scenes)
            .exclude(file="")
            .exclude(file=None)
            .count()
        )
        total_cost += scene_images_count * costs.get(f"scene_image_{video.mode}", 0)

    return total_cost


def charge_user(user, limit_field: str, video) -> float:
    if user is None:
        return 0

    cost = calculate_total_cost(video)

    get_user_model().objects.filter(pk=user.pk).update(
        **{limit_field: F(limit_field) - cost}
    )
    user.refresh_from_db(fields=[limit_field])

    logger.info(
        "Charged %s %.2f for video %s (%s remaining)",
        user.pk,
        cost,
        video.pk,
        getattr(user, limit_field, None),
    )

    return cost
