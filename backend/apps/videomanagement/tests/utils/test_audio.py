import base64
from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.baker_recipes import user_custom_tts_provider
from apps.apikeysmanagement.models import UserCustomTTSProvider
from apps.usermanagement.baker_recipes import user as user_recipe
from ...baker_recipes import scene, video, voice_model
from ...models import Scene
from ...utils import audio_utils
from ...utils.audio_utils import (
    ApiSyn,
    make_scene_speech,
    save,
    update_scene,
)
from apps.videomanagement.utils.tts_utils import tts_from_custom_provider


class SaveTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()

    def test_save_returns_none_when_syn_is_none(self):
        self.assertIsNone(save(None, "hello", "/tmp/test.wav", user=self.user))

    @patch.object(audio_utils, "tts_from_open_api")
    @patch("os.path.exists", return_value=True)
    def test_save_calls_builtin_provider(self, mock_exists, mock_openai):
        syn = ApiSyn(provider="open_ai", path="onyx")
        result = save(syn, "hello", "/tmp/test.wav", user=self.user)

        mock_openai.assert_called_once_with("hello", "/tmp/test.wav", "onyx", user=self.user)
        self.assertEqual(result, "/tmp/test.wav")

    @patch.object(audio_utils, "tts_from_custom_provider")
    @patch("os.path.exists", return_value=True)
    def test_save_calls_custom_provider(self, mock_exists, mock_custom):
        syn = ApiSyn(provider="my_custom_tts", path="voice_123", custom_provider_name="my_custom_tts")
        result = save(syn, "hello", "/tmp/test.wav", user=self.user)

        mock_custom.assert_called_once_with(
            "hello", "/tmp/test.wav", "voice_123", user=self.user, custom_provider_name="my_custom_tts"
        )
        self.assertEqual(result, "/tmp/test.wav")

    @patch("os.path.exists", return_value=False)
    def test_save_returns_none_if_file_not_created(self, mock_exists):
        syn = ApiSyn(provider="open_ai", path="onyx")
        with patch.object(audio_utils, "tts_from_open_api"):
            result = save(syn, "hello", "/tmp/test.wav", user=self.user)
        self.assertIsNone(result)


class TTSFromCustomProviderTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()
        self.custom_provider = user_custom_tts_provider.make(
            user=self.user,
            name="my_custom_tts",
            endpoint_url="https://api.customtts.com/v1/synthesize",
            text_field_name="input_text",
            voice_field_name="voice_id",
        )

    def test_raises_api_exception_when_provider_not_found(self):
        with self.assertRaises(APIException) as ctx:
            tts_from_custom_provider(
                "hello", "/tmp/out.wav", "voice_123", user=self.user, custom_provider_name="non_existent"
            )
        self.assertIn("non_existent", str(ctx.exception))

    @patch("requests.post")
    @patch("builtins.open", new_callable=MagicMock)
    def test_successful_custom_tts_request(self, mock_open, mock_post):
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_post.return_value = mock_response

        with patch.object(UserCustomTTSProvider, "get_auth_headers", return_value=({}, None)):
            res = tts_from_custom_provider(
                "hello", "/tmp/out.wav", "v1", user=self.user, custom_provider_name="my_custom_tts"
            )

        mock_post.assert_called_once_with(
            "https://api.customtts.com/v1/synthesize",
            json={"input_text": "hello", "voice_id": "v1"},
            headers={},
            auth=None,
            timeout=30,
        )
        self.assertEqual(res, mock_response)


class MakeSceneSpeechTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()
        self.voice = voice_model.make(created_by=self.user)
        self.video = video.make(created_by=self.user, voice_model=self.voice)

    def test_synthesises_the_line_and_hangs_it_on_the_scene(self):
        with patch.object(audio_utils, "save", return_value="dialogues/a.wav") as save_mock:
            scene = make_scene_speech(self.video, " hello ", is_last=True)

        self.assertEqual(scene.file, "dialogues/a.wav")
        self.assertEqual(scene.text, "hello")
        self.assertTrue(scene.is_last)
        self.assertEqual(save_mock.call_args.args[1], "hello")

    def test_still_creates_the_scene_when_nothing_is_narrated(self):
        with patch.object(audio_utils, "save") as save_mock:
            scene_obj = make_scene_speech(self.video, "hello", False, narrate=False)

        save_mock.assert_not_called()
        self.assertFalse(scene_obj.file)
        self.assertEqual(Scene.objects.count(), 1)


class UpdateSceneTests(TestCase):
    def setUp(self):
        self.user = user_recipe.make()

    def test_resynthesises_the_line_and_saves_the_new_file(self):
        narrated = video.make(avatar=None, created_by=self.user)
        line = scene.make(video=narrated)

        with (
            patch.object(audio_utils, "ApiSyn"),
            patch.object(audio_utils, "save", return_value="dialogues/new.wav") as save_mock,
        ):
            update_scene(line)

        line.refresh_from_db()
        self.assertEqual(line.file, "dialogues/new.wav")
        self.assertEqual(save_mock.call_args.args[1], line.text)