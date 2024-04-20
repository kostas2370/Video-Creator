from django.core.management import BaseCommand
from django.conf import settings
from ...utils.gpt_utils import get_voices_from_labs
from ...models import VoiceModels


class Command(BaseCommand):
    help = "Setup the eleven labs voices"
    def handle(self, *args, **options):
        if not settings.XI_API_KEY:
            print("You need to add the XI_API_KEY")
            return

        voices = get_voices_from_labs()
        for voice in voices:
            voice_exists = VoiceModels.objects.filter(name = voice["name"]).count() > 0
            if voice_exists:
                continue

            VoiceModels.objects.create(name = voice["name"],
                                       provider = "eleven_labs",
                                       type = "API",
                                       path = voice["voice_id"],
                                       sample = voice["preview_url"])

        print("Voices got added successfully")


