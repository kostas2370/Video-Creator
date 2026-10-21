from copy import copy
from functools import partial

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.usermanagement.models import Notification

from .events import publish_update
from .models import Scene, SceneImage, Video
from .services.media.archive import (
    VIDEO_VISUAL_LABELS,
    archive_scene_visual,
    archive_video_visual,
)


@receiver(post_save, sender=Video)
@receiver(post_delete, sender=Video)
def video_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(f"video.{instance.pk}", video_id=instance.pk, using=using)


@receiver(post_save, sender=Scene)
@receiver(post_delete, sender=Scene)
def scene_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(
            f"video.{instance.video_id}",
            video_id=instance.video_id,
            kind="scene",
            scene_id=instance.pk,
            using=using,
        )


@receiver(post_save, sender=SceneImage)
@receiver(post_delete, sender=SceneImage)
def visual_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(
            f"video.{instance.scene.video_id}",
            video_id=instance.scene.video_id,
            kind="scene",
            scene_id=instance.scene_id,
            using=using,
        )


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(
            f"notifications.{instance.user_id}", kind="notification", using=using
        )


@receiver(pre_save, sender=SceneImage)
@receiver(pre_save, sender=Video)
def mark_changed_visual_files(
    sender, instance, raw=False, update_fields=None, **kwargs
):
    if raw:
        return
    fields = {"file"} if sender is SceneImage else set(VIDEO_VISUAL_LABELS)
    selected = fields if update_fields is None else fields.intersection(update_fields)
    if not selected or instance._state.adding:
        instance._library_fields = selected
        return
    previous = sender.objects.filter(pk=instance.pk).values(*selected).first() or {}
    instance._library_fields = {
        name
        for name in selected
        if not getattr(instance, name)._committed
        or previous.get(name) != getattr(instance, name).name
    }


@receiver(post_save, sender=SceneImage)
@receiver(post_save, sender=Video)
def archive_saved_visuals(sender, instance, raw=False, **kwargs):
    if raw:
        return
    archive = archive_scene_visual if sender is SceneImage else archive_video_visual
    for name in getattr(instance, "_library_fields", ()):
        # Freeze each file before another save can replace it on this instance.
        source = copy(getattr(instance, name))
        transaction.on_commit(
            partial(archive, instance, source), using=kwargs.get("using")
        )
