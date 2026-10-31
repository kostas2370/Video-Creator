import logging
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.db import close_old_connections

from apps.apikeysmanagement.models import Provider
from apps.videomanagement.integrations.visuals import (
    ImageProviderRegistry,
    openai_images,
)
from apps.videomanagement.models import ImageMode, MediaAsset, Scene, SceneImage, Video, VideoType
from apps.videomanagement.services.scenes.narration import ensure_scene_rows
from apps.videomanagement.utils.audio_editing import duration_override
from apps.videomanagement.utils.file_utils import check_if_video, stored_file_exists
from apps.videomanagement.utils.frames import still_from_video
from apps.videomanagement.utils.prompt_utils import (
    with_shot_plan,
    with_visual_continuity,
)
from apps.videomanagement.utils.timing import file_timing

logger = logging.getLogger(__name__)
MAX_PARALLEL_STILL_IMAGES = 3


def scene_narration_duration(scene: Scene) -> float:
    return file_timing(scene.file).get("audio_duration") or 0


def visual_generation_duration(scene):
    if (scene.video.settings or {}).get("narration", True):
        return scene_narration_duration(scene)
    return (
        duration_override(scene)
        or (scene.shot_plan or {}).get("target_duration")
        or scene_narration_duration(scene)
    )


def planned_visual_prompt(scene, prompt, mode, provider):
    if mode != ImageMode.AI:
        return prompt
    return with_visual_continuity(
        with_shot_plan(
            prompt,
            scene.shot_plan or {},
            video=ImageProviderRegistry.is_video(
                provider, user=scene.video.created_by, mode=mode
            ),
        ),
        (scene.video.settings or {}).get("visual_continuity", ""),
    )


def continuation_frame(video: Video, text: str, path: str, scene=None):
    """Use the last visible frame when narration trims the generated clip."""
    if not path:
        return None
    previous = (
        scene if scene is not None else video.scenes.filter(text=text.strip()).first()
    )
    duration = (
        scene_narration_duration(previous)
        if previous and (video.settings or {}).get("narration", True)
        else duration_override(previous)
        if previous
        else 0
    )
    options = {"end_time": duration} if duration else {}
    return still_from_video(path, f"{video.dir_name}/images/", **options)


def uploaded_reference(video, provider):
    """Style-only video references guide text without imposing a source first frame."""
    if not video.reference_image or not stored_file_exists(video.reference_image):
        return None
    if (video.settings or {}).get(
        "reference_role"
    ) == "style" and ImageProviderRegistry.is_video(
        provider,
        user=video.created_by,
    ):
        return None
    return video.reference_image.path


def reference_role_for(video, reference):
    if reference and video.reference_image and reference == video.reference_image.path:
        return (video.settings or {}).get("reference_role", "both")
    # Generated identity anchors and preceding clip frames keep their whole look.
    return "both"


def character_starting_frame(video, prompt, style, provider, mode, user, scene=None, description=None):
    if not (video.settings or {}).get("character_references") or mode != ImageMode.AI:
        return None
    if not ImageProviderRegistry.supports_reference(provider or Provider.OPENAI):
        raise ValueError(
            "Choose a visual provider with reference-image support for this cast."
        )
    if not stored_file_exists(video.reference_image):
        raise ValueError(
            "The episode character reference is missing. Restore it before generating shots."
        )
    if not ImageProviderRegistry.is_video(provider, user=user, mode=mode):
        return None
    context = {
        "prompt": prompt, "style": style, "cast": video.reference_image.name,
        "format": (video.settings or {}).get("video_format", "PORTRAIT"),
    }
    key = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    if (scene is not None and scene.starting_asset_id
            and scene.starting_image_context.get("key") == key
            and stored_file_exists(scene.starting_asset.file)):
        return scene.starting_asset.file.path
    frame = openai_images.generate_openai_image(
        "Create the starting frame of this single film shot. The reference is a labeled "
        "character identity sheet, not a scene composition. Use only the characters called "
        "for in this shot. Preserve their faces, anatomy and distinguishing features. "
        "Do not reproduce the sheet, panels, labels, or neutral studio backgrounds. "
        "Compose the actual story setting and action.\n" + prompt,
        f"{video.dir_name}/images/",
        style=style,
        user=user,
        reference=video.reference_image.path,
        reference_role="character",
        title=f"{video.title} · Scene {scene.position} starting image" if scene else "Character starting image",
        video_format=(video.settings or {}).get("video_format", "PORTRAIT"),
    )
    if not frame:
        raise RuntimeError("Could not create the character shot's starting image.")
    if scene is not None:
        from django.core.files import File
        with open(frame, "rb") as source:
            asset = MediaAsset.from_visual(
                user=user, upload=File(source, name="starting-image.png"),
                title=f"{video.title} · Scene {scene.position} starting image",
                tags=["starting image"], kind=MediaAsset.Kind.IMAGE, source_video=video,
            )
        if "starting image" not in asset.tags:
            asset.tags = list(dict.fromkeys([*asset.tags, "starting image"]))
            if not asset.source_video_id:
                asset.source_video = video
            asset.save(update_fields=["tags", "source_video"])
        scene.starting_asset = asset
        scene.starting_image_context = {
            "key": key, "description": description or prompt, "style": style,
        }
        scene.save(update_fields=["starting_asset", "starting_image_context"])
        return asset.file.path
    return frame


def create_image_scene(
    video: Video,
    image: str,
    text: str,
    dir_name: str,
    mode: str = ImageMode.WEB,
    provider: str = None,
    style: str = "vivid",
    title: str = "",
    reference: str = None,
    with_audio: bool = False,
    user=None,
    scene=None,
    *args,
    **kwargs,
) -> str:
    """
    Create a scene with an image and text.

    Parameters:
    -----------
    video : Video
        The video the scene belongs to.
    image : str
        The image URL or path.
    text : str
        The text content for the scene.
    dir_name : str
        The directory path where the image will be saved.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    provider : str, optional
        The provider for image downloading. Default is None.
    style : str, optional
        The style for image generation (applicable if mode is not "WEB"). Default is an empty string.
    title : str, optional
        The title for the image (applicable if mode is not "WEB"). Default is an empty string.
    with_audio : bool, optional
        Whether the scene should play the visual's own sound. Only ever true for a
        generated video clip — a still has nothing to play.

    Returns:
    --------
    None

    Notes:
    ------
    - This function creates a scene with an image.
    - The image is downloaded or generated based on the mode and provider specified.
    - The downloaded image is saved in the specified directory path.
    - If an exception occurs during image downloading or creation, it is logged,
      and the scene is created with a None image.
    """
    scene = (
        scene if scene is not None else video.scenes.filter(text=text.strip()).first()
    )
    if scene is None:
        logger.error("No scene for %r; skipping its visual", text[:60])
        return None

    try:
        generate = ImageProviderRegistry.resolve(mode, provider)
        visual_prompt = planned_visual_prompt(scene, image, mode, provider)
        reference = (
            character_starting_frame(video, visual_prompt, style, provider, mode, user, scene=scene, description=image)
            or reference
        )
        downloaded_image = generate(
            visual_prompt,
            f"{dir_name}/images/",
            style=style,
            title=title,
            duration=visual_generation_duration(scene),
            video_format=(video.settings or {}).get("video_format", "LANDSCAPE"),
            reference=reference,
            reference_role=reference_role_for(video, reference),
            user=user,
        )
    except Exception as ex:
        logger.error(ex)
        downloaded_image = None

    saved = scene.scene_images.filter(asset__isnull=True).first() or SceneImage(scene=scene)
    saved.file = downloaded_image
    saved.prompt = image
    saved.with_audio = bool(with_audio and downloaded_image and check_if_video(downloaded_image))
    saved.save()
    return downloaded_image


def existing_visual(video: Video, text: str, scene=None):
    """Find a usable visual, including after a failed attempt left an empty row."""
    images = SceneImage.objects.filter(
        scene__video=video, scene__archived_at__isnull=True
    )
    if scene is not None:
        images = images.filter(scene=scene)
    else:
        images = images.filter(scene__text=text.strip())
    images = images.order_by("created_at")
    return next(
        (image.file.path for image in images if stored_file_exists(image.file)), None
    )


def create_image_scenes(
    video: Video,
    mode: str = ImageMode.WEB,
    style: str = "natural",
    provider=None,
    *args,
    **kwargs,
) -> None:
    """
    Create image scenes for a video.

    Parameters:
    -----------
    video : Videos
        The video object for which image scenes are created.
    mode : str, optional
        The mode for image downloading. Default is "WEB".
    style : str, optional
        The style for image generation. Default is "natural".

    Returns:
    --------
    None

    Notes:
    ------
    - This function iterates over scenes in a video's GPT answer and creates image
      scenes based on the scene descriptions.
    - The mode and style parameters determine the method and style of image creation.
    """

    dir_name = video.dir_name
    choices = video.settings or {}
    # Keep each generated scene's independent score out of the episode mix.
    # Users can still enable audio on individual visuals in the editor.
    with_audio = (
        not choices.get("narration", True)
        and choices.get("creation_mode") != "SERIES"
    )
    lines, indexed = ensure_scene_rows(video)
    pairs = [(line, indexed[index]) for index, line in enumerate(lines)]
    pending = [
        (line, scene)
        for line, scene in pairs
        if existing_visual(video, line.text, scene) is None
    ]

    if not pending:
        return

    is_video = ImageProviderRegistry.is_video(
        provider, user=video.created_by, mode=mode
    )
    shared_image_reference = mode == ImageMode.AI and provider in (
        None,
        "",
        Provider.OPENAI,
    )
    if not is_video and not shared_image_reference:
        with ThreadPoolExecutor(
            max_workers=min(MAX_PARALLEL_STILL_IMAGES, len(pending)),
            thread_name_prefix="scene-image",
        ) as pool:
            futures = [
                pool.submit(
                    _create_image_scene_in_thread,
                    video=video,
                    scene=scene,
                    image=line.image_description,
                    text=line.text,
                    dir_name=dir_name,
                    mode=mode,
                    style=style,
                    title=video.title,
                    provider=provider,
                    with_audio=with_audio,
                    user=video.created_by,
                )
                for line, scene in pending
            ]
            for future in futures:
                future.result()
        return

    reference = uploaded_reference(video, provider)
    for line, scene in pairs:
        # Walk completed scenes too, so carry-on recovers the correct reference.
        produced = existing_visual(video, line.text, scene)
        if produced is None:
            produced = create_image_scene(
                video=video,
                scene=scene,
                image=line.image_description,
                text=line.text,
                dir_name=dir_name,
                mode=mode,
                style=style,
                title=video.title,
                provider=provider,
                reference=reference,
                with_audio=with_audio,
                user=video.created_by,
            )
        if (video.settings or {}).get("character_references"):
            reference = uploaded_reference(video, provider)
        elif is_video:
            # A failed shot breaks the chain; never continue from a stale frame.
            reference = continuation_frame(video, line.text, produced, scene=scene)
        elif reference is None and produced:
            # Keep the original identity anchor instead of accumulating image drift.
            reference = produced


def _create_image_scene_in_thread(**kwargs):
    close_old_connections()
    try:
        return create_image_scene(**kwargs)
    finally:
        close_old_connections()


def scene_reference(scene: Scene, video: Video, provider):
    """Select an identity anchor or the preceding scene's final frame."""
    if video.mode != ImageMode.AI:
        return None
    uploaded = uploaded_reference(video, provider)
    if (video.settings or {}).get("character_references"):
        return uploaded
    if provider in (None, "", Provider.OPENAI) and uploaded:
        return uploaded
    if provider in (None, "", Provider.OPENAI):
        for image in SceneImage.objects.filter(
            scene__video=video, scene__archived_at__isnull=True
        ).order_by("scene__position", "created_at"):
            if stored_file_exists(image.file) and not check_if_video(image.file.path):
                return image.file.path
    elif ImageProviderRegistry.is_video(provider, user=video.created_by):
        previous = (
            video.scenes.filter(position__lt=scene.position)
            .order_by("-position")
            .first()
        )
        if previous is None:
            return uploaded
        return continuation_frame(
            video,
            previous.text,
            existing_visual(video, previous.text, previous),
            scene=previous,
        )
    return None


def generate_new_image(
    scene_image: SceneImage, video: Video, style: str = None, *args, **kwargs
) -> SceneImage:
    """
    Generate a new image for a scene image associated with a video.

    Parameters:
    -----------
    scene_image : SceneImage
        The scene image object for which a new image is generated.
    video : Videos
        The video object associated with the scene image.
    style : str, optional
        The style for image generation. Default is "vivid".

    Returns:
    --------
    SceneImage
        The updated scene image object with the new image.

    """
    context = scene_image.scene.starting_image_context
    style = style if style is not None else (
        context.get("style", "natural")
        if context.get("description") == scene_image.prompt
        else (video.settings or {}).get("style", "natural")
    )
    provider = (video.settings or {}).get("provider")
    mode = video.mode
    if video.video_type == VideoType.MANUAL:
        mode, provider = ImageMode.AI, Provider.OPENAI
        Path(video.dir_name, "images").mkdir(parents=True, exist_ok=True)
    generate = ImageProviderRegistry.resolve(mode, provider)
    visual_prompt = planned_visual_prompt(
        scene_image.scene, scene_image.prompt or "", mode, provider
    )
    starting_frame = character_starting_frame(
        video, visual_prompt, style, provider, mode, video.created_by,
        scene=scene_image.scene, description=scene_image.prompt,
    )
    if starting_frame:
        kwargs["reference"] = starting_frame
    if "reference" not in kwargs:
        kwargs["reference"] = scene_reference(scene_image.scene, video, provider)
    kwargs.setdefault("reference_role", reference_role_for(video, kwargs["reference"]))
    kwargs.setdefault("duration", visual_generation_duration(scene_image.scene))
    kwargs.setdefault(
        "video_format", (video.settings or {}).get("video_format", "LANDSCAPE")
    )
    img = generate(
        visual_prompt,
        f"{video.dir_name}/images/",
        *args,
        style=style,
        title=video.title,
        user=video.created_by,
        **kwargs,
    )

    if not img:
        raise RuntimeError("The visual provider returned no image")
    scene_image.file = img
    scene_image.save()

    return scene_image
