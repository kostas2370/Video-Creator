from functools import partial

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import ApiKeys, Provider
from .tasks import import_user_voices

VOICE_KEY_FIELDS = {
    "elevenlabs_key": Provider.ELEVENLABS,
    "sixtydb_key": Provider.SIXTYDB,
}


@receiver(pre_save, sender=ApiKeys)
def remember_voice_keys(sender, instance, **kwargs):
    if not instance.pk:
        instance._voice_keys_before = dict.fromkeys(VOICE_KEY_FIELDS, "")
        return

    stored = ApiKeys.objects.filter(pk=instance.pk).first()
    instance._voice_keys_before = {
        field: getattr(stored, field, "") or "" for field in VOICE_KEY_FIELDS
    }


@receiver(post_save, sender=ApiKeys)
def import_voices_for_new_keys(sender, instance, **kwargs):
    before = getattr(instance, "_voice_keys_before", {})

    for field, provider in VOICE_KEY_FIELDS.items():
        current = getattr(instance, field, "") or ""
        if not current or current == before.get(field, ""):
            continue

        transaction.on_commit(
            partial(import_user_voices.delay, instance.user_id, provider)
        )
