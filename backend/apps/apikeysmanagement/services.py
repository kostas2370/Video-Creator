from apps.videomanagement import tasks


def queue_voice_refresh(provider):
    tasks.update_user_voices.delay(provider.user_id, provider.name)
