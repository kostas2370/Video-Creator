from django.conf import settings
from django.core.management import BaseCommand

from ...models import VoiceModel
from ...utils.gpt_utils import get_voices_from_labs


class Command(BaseCommand):
    help = "Setup the eleven labs voices"

    def handle(self, *args, **options):
        if not settings.XI_API_KEY:
            self.stderr.write(self.style.ERROR("You need to add the XI_API_KEY"))
            return

        voices = get_voices_from_labs()
        for voice in voices:
            voice_exists = VoiceModel.objects.filter(name=voice["name"]).count() > 0
            if voice_exists:
                continue

            VoiceModel.objects.create(
                name=voice["name"],
                provider="eleven_labs",
                type="API",
                path=voice["voice_id"],
                sample=voice["preview_url"],
            )

        self.stdout.write(self.style.SUCCESS("Added new voice(s) successfully."))
