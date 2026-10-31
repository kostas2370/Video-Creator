from django.apps import apps
from django.db import models, transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_cleanup.signals import cleanup_pre_delete

from apps.usermanagement.models import Notification

from .events import publish_update
from .models import MediaAsset, Scene, SceneImage, Video
from .utils.composer.scene_cache import remove_project_cache


@receiver(post_delete, sender=Video)
def remove_render_cache(sender, instance, using, **kwargs):
    video_id = instance.pk
    transaction.on_commit(lambda: remove_project_cache(video_id), using=using)


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


@receiver(cleanup_pre_delete, sender=MediaAsset)
@receiver(cleanup_pre_delete, sender=Scene)
def preserve_shared_asset_file(sender, file, file_name, **kwargs):
    # Cleanup runs after commit. Include archived scenes and all media-bearing
    # models so a shared narration, logo, or library file survives its first owner.
    for model in apps.get_models():
        fields = [field for field in model._meta.fields if isinstance(field, models.FileField)]
        if not fields:
            continue
        references = models.Q()
        for field in fields:
            references |= models.Q(**{field.name: file_name})
        if model._base_manager.filter(references).exists():
            file.name = None
            return


@receiver(post_save, sender=Video)
@receiver(post_save, sender="series.VideoSeries")
@receiver(post_save, sender="series.CharacterReference")
@receiver(post_save, sender=Scene)
def reference_saved(sender, instance, **kwargs):
    if not kwargs.get("raw"):
        from .services.media.references import archive_reference
        archive_reference(instance)
