import io
import shutil
import subprocess
import wave
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.apikeysmanagement.baker_recipes import api_keys
from apps.apikeysmanagement.models import Provider
from apps.usermanagement.baker_recipes import user
from ...baker_recipes import voice_model
from ...models import AIUsage, VoiceModel
from ...services.custom_voices import key_fingerprint, normalized_sample
from ...tasks import update_user_voices
from ...utils.tts_utils import tts_from_elevenlabs


@override_settings(XI_API_KEY="service-key")
class CustomVoiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.remote = patch("apps.videomanagement.services.custom_voices.requests.request")
        self.http = self.remote.start()
        self.addCleanup(self.remote.stop)
        self.http.return_value = self.response({"voice_id": "clone123", "requires_verification": False})

    @staticmethod
    def response(data=None, status=200, content=b"audio", content_type="audio/mpeg"):
        response = Mock(status_code=status, content=content, headers={"Content-Type": content_type})
        response.json.return_value = data
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
        return response

    def clone(self, **kwargs):
        values = dict(created_by=self.user, provider=Provider.ELEVENLABS, path="clone123",
                      is_cloned=True, clone_key_source="service", clone_key_fingerprint=key_fingerprint("service-key"))
        return voice_model.make(**{**values, **kwargs})

    def upload(self, **kwargs):
        values = {"name": "My voice", "consent": "true", "file": SimpleUploadedFile("voice.wav", b"audio")}
        with patch("apps.videomanagement.services.custom_voices.normalized_sample", return_value=b"wav"):
            return self.client.post(reverse("voicemodel-clone"), {**values, **kwargs}, format="multipart")

    def test_creates_private_voice_with_consent_and_the_effective_key(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        voice = VoiceModel.objects.get()
        self.assertTrue(voice.is_cloned)
        self.assertEqual(voice.created_by, self.user)
        self.assertIsNotNone(voice.consented_at)
        self.assertNotIn("clone_key_fingerprint", response.data)
        call = self.http.call_args
        self.assertEqual(call.kwargs["headers"], {"xi-api-key": "service-key"})
        self.assertEqual(call.kwargs["files"], [("files", ("sample.wav", b"wav", "audio/wav"))])
        self.assertIn(voice, VoiceModel.objects.available_to(self.user))
        self.assertNotIn(voice, VoiceModel.objects.available_to(user.make()))
        self.assertNotIn(voice, VoiceModel.objects.available_to(None))

    def test_uses_personal_key_and_hides_clone_after_switching_accounts(self):
        self.user.use_service_api_keys = False
        self.user.save(update_fields=["use_service_api_keys"])
        api_keys.make(user=self.user, elevenlabs_key="personal-key")
        self.assertEqual(self.upload().status_code, 201)
        voice = VoiceModel.objects.get()
        self.assertEqual(voice.clone_key_source, "user")
        self.assertEqual(self.http.call_args.kwargs["headers"]["xi-api-key"], "personal-key")
        self.assertIn(voice, VoiceModel.objects.available_to(self.user))
        self.user.use_service_api_keys = True
        self.user.save(update_fields=["use_service_api_keys"])
        self.assertNotIn(voice, VoiceModel.objects.available_to(self.user))
        self.assertEqual(len(self.client.get(reverse("voicemodel-mine")).data), 1)
        self.http.reset_mock()
        self.assertEqual(self.client.post(reverse("voicemodel-preview", args=[voice.pk])).status_code, 400)
        self.assertEqual(self.client.delete(reverse("voicemodel-detail", args=[voice.pk])).status_code, 400)
        self.http.assert_not_called()

    def test_rejects_missing_consent_invalid_upload_and_missing_key(self):
        for consent in ("false", ""):
            self.assertEqual(self.upload(consent=consent).status_code, 400)
        self.assertEqual(self.upload(name=" ").status_code, 400)
        self.assertEqual(self.upload(file=SimpleUploadedFile("huge.wav", b"x" * (20 * 1024 * 1024 + 1))).status_code, 400)
        with override_settings(XI_API_KEY=""):
            self.assertEqual(self.upload().status_code, 400)
        self.http.assert_not_called()
        self.assertFalse(VoiceModel.objects.exists())

    def test_caps_clones_before_creating_another_remote_voice(self):
        for index in range(3):
            self.clone(path=f"clone{index}")
        self.assertEqual(self.upload().status_code, 400)
        self.http.assert_not_called()

    def test_failed_or_malformed_provider_response_does_not_save_voice(self):
        for data, status in (({}, 200), ([], 200), ({"voice_id": "../../secret"}, 200), ({}, 403), ({}, 429)):
            cache.clear()
            self.http.return_value = self.response(data, status)
            self.assertEqual(self.upload().status_code, 502)
            self.assertFalse(VoiceModel.objects.exists())
        cache.clear()
        self.http.side_effect = requests.Timeout()
        self.assertEqual(self.upload().status_code, 502)

    def test_pending_verification_stays_manageable_but_unselectable(self):
        self.http.return_value = self.response({"voice_id": "clone123", "requires_verification": True})
        self.assertEqual(self.upload().status_code, 201)
        voice = VoiceModel.objects.get()
        self.assertNotIn(voice, VoiceModel.objects.available_to(self.user))
        self.assertEqual(len(self.client.get(reverse("voicemodel-mine")).data), 1)
        self.http.reset_mock()
        self.assertEqual(self.client.post(reverse("voicemodel-preview", args=[voice.pk])).status_code, 400)
        self.http.assert_not_called()
        self.http.return_value = self.response({"voice_verification": {"requires_verification": False, "is_verified": True}})
        response = self.client.post(reverse("voicemodel-refresh", args=[voice.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(voice, VoiceModel.objects.available_to(self.user))

    def test_preview_is_private_audio_and_records_usage(self):
        voice = self.clone()
        response = self.client.post(reverse("voicemodel-preview", args=[voice.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"audio")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(AIUsage.objects.get().user, self.user)
        self.http.return_value = self.response({}, content_type="application/json")
        self.assertEqual(self.client.post(reverse("voicemodel-preview", args=[voice.pk])).status_code, 502)

    def test_other_users_cannot_manage_or_preview_even_as_superuser(self):
        voice = self.clone(created_by=user.make())
        for name in ("preview", "refresh"):
            self.assertEqual(self.client.post(reverse(f"voicemodel-{name}", args=[voice.pk])).status_code, 404)
        self.user.is_superuser = True
        self.user.save(update_fields=["is_superuser"])
        self.assertEqual(self.client.delete(reverse("voicemodel-detail", args=[voice.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("voicemodel-mine")).data, [])
        self.http.assert_not_called()

    def test_delete_removes_remote_voice_first_and_keeps_record_on_failure(self):
        voice = self.clone()
        url = reverse("voicemodel-detail", args=[voice.pk])
        self.http.return_value = self.response({}, status=503)
        self.assertEqual(self.client.delete(url).status_code, 502)
        self.assertTrue(VoiceModel.objects.filter(pk=voice.pk).exists())
        self.http.return_value = self.response({}, status=404)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(VoiceModel.objects.filter(pk=voice.pk).exists())

    def test_rotated_key_does_not_use_or_delete_a_clone(self):
        voice = self.clone()
        with override_settings(XI_API_KEY="new-key"):
            self.assertNotIn(voice, VoiceModel.objects.available_to(self.user))
            self.assertEqual(self.client.delete(reverse("voicemodel-detail", args=[voice.pk])).status_code, 400)
        self.http.assert_not_called()

    def test_refresh_and_shared_setup_never_publish_or_remove_clones(self):
        voice = self.clone()
        with patch("apps.videomanagement.utils.tts_utils.get_voices_from_elevenlabs", return_value=[]):
            update_user_voices(self.user.pk, Provider.ELEVENLABS)
        self.assertTrue(VoiceModel.objects.filter(pk=voice.pk).exists())
        remote_voices = [{"voice_id": voice.path, "name": voice.name, "preview_url": ""}]
        with patch("apps.videomanagement.utils.tts_utils.get_voices_from_elevenlabs", return_value=remote_voices):
            update_user_voices(user.make().pk, Provider.ELEVENLABS)
        with patch("apps.videomanagement.management.commands.setup_elevenlabs.get_voices_from_elevenlabs", return_value=remote_voices):
            call_command("setup_elevenlabs", stdout=io.StringIO())
        self.assertEqual(VoiceModel.objects.filter(path=voice.path).count(), 1)

    def test_saved_video_cannot_bypass_clone_ownership_or_verification(self):
        voice = self.clone()
        with patch("apps.videomanagement.utils.tts_utils.requests.post") as speech:
            with self.assertRaises(PermissionDenied):
                tts_from_elevenlabs("Hello", "/tmp/unused.wav", voice.path, user=user.make())
            voice.requires_verification = True
            voice.save()
            with self.assertRaises(ValidationError):
                tts_from_elevenlabs("Hello", "/tmp/unused.wav", voice.path, user=self.user)
            speech.assert_not_called()

    def test_creation_is_throttled(self):
        for _ in range(5):
            self.assertEqual(self.upload(consent="false").status_code, 400)
        self.assertEqual(self.upload().status_code, 429)
        self.http.assert_not_called()

    def test_unauthenticated_requests_cannot_clone(self):
        self.client.force_authenticate(None)
        self.assertIn(self.upload().status_code, (401, 403))
        self.http.assert_not_called()


class SampleValidationTests(TestCase):
    @staticmethod
    def audio(seconds):
        output = io.BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\0\0" * (8000 * seconds))
        return SimpleUploadedFile("sample.wav", output.getvalue(), "audio/wav")

    def test_rejects_unreadable_audio(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg required")
        with self.assertRaises(ValidationError):
            normalized_sample(SimpleUploadedFile("fake.mp3", b"not audio"))

    def test_normalizes_audio_and_enforces_duration(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg required")
        result = normalized_sample(self.audio(10))
        with wave.open(io.BytesIO(result), "rb") as audio:
            self.assertEqual(audio.getframerate(), 22050)
            self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), 10)
        for seconds in (1, 121):
            with self.subTest(seconds=seconds), self.assertRaises(ValidationError):
                normalized_sample(self.audio(seconds))

    def test_reads_webm_recordings_from_browser(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg required")
        encoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", "pipe:0", "-f", "webm", "-c:a", "libopus", "pipe:1"],
            input=self.audio(12).read(), capture_output=True, check=True, timeout=10,
        ).stdout
        decoded = normalized_sample(SimpleUploadedFile("recording.webm", encoded, "audio/webm"))
        with wave.open(io.BytesIO(decoded), "rb") as audio:
            self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), 12, delta=0.1)
