from django.core.management import BaseCommand

from apps.apikeysmanagement.models import ApiKeys, Provider

from ...models import VoiceModel
from ...utils.tts_utils import get_voices_from_elevenlabs


class Command(BaseCommand):
    help = "Setup the ElevenLabs voices"

    def handle(self, *args, **options):
        if not ApiKeys.key_for(None, Provider.ELEVENLABS):
            self.stderr.write(self.style.ERROR("You need to add the XI_API_KEY"))
            return

        voices = get_voices_from_elevenlabs()
        private_paths = set(VoiceModel.objects.filter(is_cloned=True, provider=Provider.ELEVENLABS).values_list("path", flat=True))
        for voice in voices:
            if voice["voice_id"] in private_paths:
                continue
            voice_exists = VoiceModel.objects.filter(
                created_by=None, provider=Provider.ELEVENLABS, path=voice["voice_id"]
            ).exists()
            if voice_exists:
                continue

            VoiceModel.objects.create(
                name=voice["name"],
                provider=Provider.ELEVENLABS,
                type="API",
                path=voice["voice_id"],
                sample=voice["preview_url"],
            )

        self.stdout.write(self.style.SUCCESS("Added new voice(s) successfully."))
