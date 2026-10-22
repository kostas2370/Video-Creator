"""Assign scene positions while the caller holds the parent video's row lock."""

from apps.videomanagement.models import Scene


def assign_scene_positions(video, active_scenes):
    """Keep active scenes first and archived rows outside their occupied range."""
    archived = list(
        Scene.all_objects.filter(video=video, archived_at__isnull=False)
        .select_for_update()
        .order_by("position")
    )
    ordered = [*active_scenes, *archived]
    if not ordered:
        return
    offset = max(scene.position for scene in ordered)
    # Move every row above the occupied range before compacting. This preserves
    # the unique video/position constraint on databases without deferred checks.
    for position, scene in enumerate(ordered, offset + 1):
        scene.position = position
    Scene.all_objects.bulk_update(ordered, ["position"])
    for position, scene in enumerate(ordered, 1):
        scene.position = position
    Scene.all_objects.bulk_update(ordered, ["position"])
