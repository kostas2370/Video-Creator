from django.db.models import Q


from ..models import Scene, Videos, SceneImage


costs = {"twitch_scene": 0.08,
         "scene_API": 0.02,
         "scene_LOCAL": 0.01,
         "scene_image_AI": 0.08,
         "scene_image_WEB": 0.04,
         "scene_image_DALL-E": 0.08}


def calculate_total_cost(video):
    total_cost = 0
    scenes = Scene.objects.filter(prompt__video_prompt__id = video.id)
    if video.video_type == "TWITCH":
        total_cost += 0.05 + scenes.count() * costs.get("twitch_scene", 0)

    if video.video_type == "AI":
        total_cost += 0.12 + scenes.count()*costs.get(f"scene_{video.voice_model.type}", 0)

        scene_images = SceneImage.objects.filter(~Q(file=None), scene__in=scenes).count()
        total_cost += scene_images * costs.get(f"scene_image_{video.mode}")

    return total_cost
