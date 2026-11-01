import math

from django.conf import settings

from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.models import VoiceModelType
from apps.videomanagement.services.scenes.visuals import visual_generation_duration

from .pricing import estimate_line, image_estimate, total_estimate

VIDEO_MODELS = {
    "runway": ("RUNWAY", "gen4.5", 2, 10),
    "kling": ("FAL", "fal-ai/kling-video/o3/pro/reference-to-video", 3, 15),
    "gemini-video": ("GEMINI", "gemini-omni-1.1-flash", 3, 10),
}


def voice_estimate(video, text, requests=1):
    voice = video.voice_model
    provider = voice.provider if voice else "Unselected voice"
    model = (
        "tts-1"
        if provider == "OPENAI"
        else (
            "eleven_multilingual_v2"
            if voice and voice.is_cloned
            else "eleven_monolingual_v1"
        )
        if provider == "ELEVENLABS"
        else ""
    )
    custom = bool(voice and voice.type == VoiceModelType.CUSTOM_API)
    return estimate_line(
        "Narration",
        "tts",
        provider,
        "" if custom else model,
        {"characters": len(text), "requests": requests},
        custom=custom,
    )


def animation_estimate(video, durations):
    provider = (video.settings or {}).get("provider")
    known = VIDEO_MODELS.get(provider)
    if known:
        name, model, minimum, maximum = known
        seconds = sum(
            max(
                minimum,
                min(maximum, math.ceil(duration or settings.SILENT_SCENE_SECONDS)),
            )
            for duration in durations
        )
        return estimate_line(
            "Animation",
            "video",
            name,
            model,
            {"seconds": seconds, "requests": len(durations)},
        )
    return estimate_line(
        "Animation",
        "video",
        provider or "Unselected provider",
        settings.SORA_MODEL if provider == "sora" else "",
        {"requests": len(durations)},
        custom=True,
    )


def media_estimate(video, storyboard=None, *, scene=None, operation="all", text=None):
    options = video.settings or {}
    narration = options.get("narration", video.video_type != "MANUAL")
    if scene is None:
        storyboard = storyboard if storyboard is not None else video.gpt_answer
        shots = (
            [
                shot
                for group in (storyboard or {}).get("scenes", [])
                for shot in group.get("sentences", [])
            ]
            if isinstance(storyboard, dict)
            else []
        )
        texts = [shot.get("sentence", "").strip() for shot in shots]
        durations = [
            max(1, len(value.split()) / 2.5)
            if narration
            else (shot.get("shot_plan") or {}).get("target_duration")
            for shot, value in zip(shots, texts)
        ]
    else:
        texts = [(scene.text if text is None else text).strip()]
        durations = [visual_generation_duration(scene)]
    count = len(texts)
    lines = []
    if narration and operation in ("all", "narration") and count:
        lines.append(voice_estimate(video, "".join(texts), requests=count))
    if count and operation in ("all", "visual", "animation"):
        provider = options.get("provider") or "OPENAI"
        is_video = ImageProviderRegistry.is_video(
            provider, user=video.created_by, mode=video.mode
        )
        character_images = is_video and options.get("character_references")
        if operation == "animation" or (
            is_video and (operation == "all" or not character_images)
        ):
            line = animation_estimate(video, durations)
            if scene is None and narration:
                line["note"] += (
                    " Duration assumes 150 spoken words per minute; billed clip lengths may differ."
                )
            if character_images and operation == "all":
                line["note"] += (
                    " Charged later, only when you choose Animate approved image."
                )
            lines.append(line)
        if operation != "animation" and (character_images or not is_video):
            if video.mode == "AI" or video.video_type == "MANUAL":
                custom = not bool(ImageProviderRegistry.registration(provider, "AI"))
                lines.append(
                    image_estimate(
                        count,
                        "OPENAI"
                        if character_images or video.video_type == "MANUAL"
                        else {
                            "midjourney": "MIDJOURNEY",
                            "stable-diffusion": "STABLE_DIFFUSION",
                        }.get(provider, provider),
                        custom=custom
                        and not character_images
                        and video.video_type != "MANUAL",
                    )
                )
    estimate = total_estimate(lines)
    estimate["note"] = (
        "One pass of media generation. Script drafting, rewrites, retries, taxes and discounts are excluded. Unknown prices are excluded from the subtotal."
    )
    return estimate
