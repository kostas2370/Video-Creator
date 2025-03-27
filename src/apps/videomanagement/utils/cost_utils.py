

from ..models import SceneImage


costs = {"twitch_scene": 0.08,
         "scene_API": 0.02,
         "scene_LOCAL": 0.01,
         "scene_image_AI": 0.08,
         "scene_image_WEB": 0.04,
         "scene_image_DALL-E": 0.08}


def calculate_total_cost(video):
    total_cost = 0
    scenes = video.prompt.scenes.all()
    scene_count = scenes.count()

    if video.video_type == "TWITCH":
        total_cost += 0.05 + scene_count * costs.get("twitch_scene", 0)

    if video.video_type == "AI":
        total_cost += 0.12 + scene_count * costs.get(f"scene_{video.voice_model.type}", 0)
        scene_images_count = SceneImage.objects.filter(scene__in=scenes).exclude(file=None).count()
        total_cost += scene_images_count * costs.get(f"scene_image_{video.mode}", 0)

    return total_cost
