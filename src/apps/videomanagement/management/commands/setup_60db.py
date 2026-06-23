from django.conf import settings
from django.core.management import BaseCommand

from ...models import VoiceModel
from ...utils.gpt_utils import get_voices_from_60db


class Command(BaseCommand):
    help = "Setup the 60db voices"

    def handle(self, *args, **options):
        if not settings.SIXTYDB_API_KEY:
            self.stderr.write(self.style.ERROR("You need to add the SIXTYDB_API_KEY"))
            return

        voices = get_voices_from_60db()
        for voice in voices:
            voice_exists = VoiceModel.objects.filter(name=voice["name"]).count() > 0
            if voice_exists:
                continue

            VoiceModel.objects.create(
                name=voice["name"],
                provider="60db",
                type="API",
                path=voice["voice_id"],
                sample=voice.get("preview_url", ""),
            )

        self.stdout.write(self.style.SUCCESS("Added new voice(s) successfully."))
