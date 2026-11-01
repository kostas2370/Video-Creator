from apps.videomanagement.integrations.base import ImageCostRequest, TTSCostRequest
from apps.videomanagement.integrations.tts import CustomTTSProvider, TTSRegistry
from apps.videomanagement.integrations.visuals.custom import CustomImageProvider

from apps.videomanagement.integrations.visuals.registry import ImageProviderRegistry
from apps.videomanagement.models import VoiceModelType
from apps.videomanagement.services.scenes.visuals import visual_generation_duration

from .pricing import estimate_line, total_estimate


def voice_estimate(video, text, requests=1):
    voice = video.voice_model
    if voice is None:
        return estimate_line(
            "Narration",
            "tts",
            "Unselected voice",
            "",
            {"characters": len(text), "requests": requests},
        )
    provider = (
        CustomTTSProvider()
        if voice.type == VoiceModelType.CUSTOM_API
        else TTSRegistry.provider(voice.provider) or CustomTTSProvider()
    )
    return provider.calculate(
        TTSCostRequest(
            text, requests=requests, voice=voice, provider_name=voice.provider
        )
    )


def animation_estimate(video, durations):
    name = (video.settings or {}).get("provider")
    registration = ImageProviderRegistry.registration(name, "AI") if name else None
    provider = (
        ImageProviderRegistry.provider(name, "AI")
        if registration and registration.capabilities.get("output_type") == "VIDEO"
        else None
    ) or CustomImageProvider()
    return provider.calculate(
        ImageCostRequest(
            count=len(durations),
            durations=tuple(durations),
            provider_name=name or "Unselected provider",
            output_type="VIDEO",
        )
    )


def media_estimate(video, storyboard=None, *, scene=None, operation="all", text=None):
    options = video.settings or {}
    generation_mode = (
        (storyboard or {}).get(
            "generation_mode", options.get("generation_mode", "STANDARD")
        )
        if isinstance(storyboard, dict)
        else options.get("generation_mode", "STANDARD")
    )
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
                image_name = (
                    "OPENAI"
                    if character_images or video.video_type == "MANUAL"
                    else provider
                )
                calculator = (
                    ImageProviderRegistry.provider(image_name, "AI")
                    or CustomImageProvider()
                )
                lines.append(
                    calculator.calculate(
                        ImageCostRequest(
                            count=count,
                            generation_mode=generation_mode,
                            provider_name=image_name,
                        )
                    )
                )
    estimate = total_estimate(lines)
    estimate["note"] = (
        "One pass of media generation. Script drafting, rewrites, retries, taxes and discounts are excluded. Unknown prices are excluded from the subtotal."
    )
    return estimate
