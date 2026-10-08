from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .events import publish_update
from apps.usermanagement.models import Notification

from .models import Scene, SceneImage, Video


@receiver(post_save, sender=Video)
@receiver(post_delete, sender=Video)
def video_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(f"video.{instance.pk}", video_id=instance.pk, using=using)


@receiver(post_save, sender=Scene)
@receiver(post_delete, sender=Scene)
def scene_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(f"video.{instance.video_id}", video_id=instance.video_id, kind="scene", scene_id=instance.pk, using=using)


@receiver(post_save, sender=SceneImage)
@receiver(post_delete, sender=SceneImage)
def visual_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(f"video.{instance.scene.video_id}", video_id=instance.scene.video_id, kind="scene", scene_id=instance.scene_id, using=using)


@receiver(post_save, sender=Notification)
@receiver(post_delete, sender=Notification)
def notification_changed(sender, instance, using, **kwargs):
    if not kwargs.get("raw"):
        publish_update(f"notifications.{instance.user_id}", kind="notification", using=using)
