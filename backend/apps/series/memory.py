"""A stable representation of the story an episode memory describes."""

import hashlib
import json

from apps.videomanagement.utils.prompt_utils import script_lines


def script_snapshot(entries):
    entries = [
        {"text": row["text"].strip(), "visual": (row["visual"] or "").strip()}
        for row in entries
    ]
    encoded = json.dumps(entries, ensure_ascii=False, sort_keys=True).encode()
    return {"entries": entries, "hash": hashlib.sha256(encoded).hexdigest()}


def storyboard_snapshot(storyboard):
    lines = (
        script_lines(storyboard)
        if isinstance(storyboard, dict) and storyboard.get("scenes")
        else []
    )
    return script_snapshot(
        [{"text": line.text, "visual": line.image_description} for line in lines]
    )


def video_script_snapshot(video):
    if video.status in ("REVIEW", "GENERATION"):
        return storyboard_snapshot(video.gpt_answer)
    scenes = list(video.scenes.all())
    if (
        not scenes
        and video.status == "FAILED"
        and not video.scenes.model.all_objects.filter(video_id=video.pk).exists()
    ):
        return storyboard_snapshot(video.gpt_answer)
    entries = []
    for scene in scenes:
        visual = next(iter(scene.scene_images.all()), None)
        entries.append({"text": scene.text, "visual": visual.prompt if visual else ""})
    return script_snapshot(entries)
