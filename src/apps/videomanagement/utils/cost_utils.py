import logging

from django.contrib.auth import get_user_model
from django.db.models import F

from ..models import SceneImage

logger = logging.getLogger(__name__)


costs = {
    "twitch_scene": 0.08,
    "scene_API": 0.02,
    "scene_LOCAL": 0.01,
    "scene_image_AI": 0.08,
    "scene_image_WEB": 0.04,
    "scene_image_DALL-E": 0.08,
}


def calculate_total_cost(video):
    total_cost = 0
    scenes = video.prompt.scenes.all()
    scene_count = scenes.count()

    if video.video_type == "TWITCH":
        total_cost += 0.05 + scene_count * costs.get("twitch_scene", 0)

    if video.video_type == "AI":
        total_cost += 0.12 + scene_count * costs.get(
            f"scene_{video.voice_model.type}", 0
        )
        scene_images_count = (
            SceneImage.objects.filter(scene__in=scenes).exclude(file=None).count()
        )
        total_cost += scene_images_count * costs.get(f"scene_image_{video.mode}", 0)

    return total_cost


def charge_user(user, limit_field: str, video) -> float:
    """
    Deduct the cost of `video` from `user`'s balance in a single UPDATE.

    Generation now runs on workers, so several jobs for the same user can finish at
    once. A read-modify-write (`user.x -= cost; user.save()`) would let those
    concurrent finishes overwrite each other's deduction and would also rewrite every
    other field on the row, so the update is pushed into the database with F().
    """
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
