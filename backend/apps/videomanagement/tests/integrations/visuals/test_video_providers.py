"""Provider contracts and failure handling. All network/media generation is mocked."""

import base64
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image
from rest_framework.exceptions import APIException

from apps.apikeysmanagement.baker_recipes import api_keys
from apps.apikeysmanagement.models import ApiKeys, Provider
from apps.apikeysmanagement.serializers import ApiKeysSerializer
from apps.videomanagement.integrations.visuals import (
    gemini_video,
    kling,
    runway,
    video_http as http,
)


@override_settings(
    VIDEO_POLL_INTERVAL=0, VIDEO_GENERATION_TIMEOUT=1, SILENT_SCENE_SECONDS=5
)
class VideoProviderTests(SimpleTestCase):
    def setUp(self):
        for name, value in (
            ("key_for", "secret-key"),
            ("image_data", "image-base64"),
            ("save_download", "saved.mp4"),
        ):
            patcher = patch.object(http, name, return_value=value)
            setattr(self, name, patcher.start())
            self.addCleanup(patcher.stop)

    def test_kling_submits_reference_and_uses_returned_queue_urls(self):
        responses = [
            {
                "status_url": "https://queue.fal.run/fal-ai/kling-video/requests/job/status",
                "response_url": "https://queue.fal.run/fal-ai/kling-video/requests/job",
            },
            {"status": "IN_QUEUE"},
            {"status": "IN_PROGRESS"},
            {"status": "COMPLETED"},
            {"video": {"url": "https://v3.fal.media/result.mp4"}},
        ]
        with (
            patch.object(http, "json_request", side_effect=responses) as request,
            patch.object(kling, "record_usage") as usage,
        ):
            self.assertEqual(
                kling.generate_from_kling(
                    "fox runs",
                    "images/",
                    duration=6.1,
                    reference="ref.png",
                    video_format="PORTRAIT",
                ),
                "saved.mp4",
            )
        body = request.call_args_list[0].kwargs["body"]
        self.assertEqual(body["duration"], "7")
        self.assertEqual(body["aspect_ratio"], "9:16")
        self.assertEqual(body["start_image_url"], "data:image/jpeg;base64,image-base64")
        self.assertIn("fox runs", body["prompt"])
        self.assertEqual(
            request.call_args_list[-1].args[1], responses[0]["response_url"]
        )
        usage.assert_called_once()
        self.assertEqual(usage.call_args.kwargs["seconds"], 7)
        self.assertNotIn("headers", self.save_download.call_args.kwargs)

    def test_kling_can_generate_without_reference(self):
        self.image_data.return_value = None
        with patch.object(
            http,
            "json_request",
            side_effect=[
                {
                    "status_url": "https://queue.fal.run/status",
                    "response_url": "https://queue.fal.run/result",
                },
                {"status": "COMPLETED"},
                {"video": {"url": "https://v3.fal.media/a.mp4"}},
            ],
        ) as request:
            kling.generate_from_kling("cat", "images/")
        self.assertNotIn("start_image_url", request.call_args_list[0].kwargs["body"])

    def test_failed_fal_job_does_not_download(self):
        with (
            patch.object(
                http,
                "json_request",
                side_effect=[
                    {
                        "status_url": "https://queue.fal.run/status",
                        "response_url": "https://queue.fal.run/result",
                    },
                    {"status": "COMPLETED", "error": "secret raw provider body"},
                ],
            ),
            self.assertRaises(APIException) as caught,
        ):
            kling.generate_from_kling("cat", "images/")
        self.assertNotIn("secret raw", str(caught.exception))
        self.save_download.assert_not_called()

    def test_runway_selects_image_endpoint_and_version(self):
        with (
            patch.object(
                http,
                "json_request",
                side_effect=[
                    {"id": "task-1"},
                    {"status": "RUNNING"},
                    {
                        "status": "SUCCEEDED",
                        "output": ["https://cdn.runwayml.com/a.mp4"],
                    },
                ],
            ) as request,
            patch.object(runway, "record_usage"),
        ):
            runway.generate_from_runway(
                "fox",
                "images/",
                duration=4.1,
                reference="ref.png",
                video_format="PORTRAIT",
            )
        call = request.call_args_list[0]
        self.assertTrue(call.args[1].endswith("/image_to_video"))
        self.assertEqual(call.kwargs["headers"]["X-Runway-Version"], "2024-11-06")
        self.assertEqual(call.kwargs["body"]["ratio"], "720:1280")
        self.assertEqual(call.kwargs["body"]["duration"], 5)
        self.assertEqual(
            call.kwargs["body"]["promptImage"], "data:image/jpeg;base64,image-base64"
        )

    def test_runway_text_generation_and_duration_cap(self):
        self.image_data.return_value = None
        with (
            patch.object(
                http,
                "json_request",
                side_effect=[
                    {"id": "task-1"},
                    {
                        "status": "SUCCEEDED",
                        "output": ["https://cdn.runwayml.com/a.mp4"],
                    },
                ],
            ) as request,
            patch.object(runway, "record_usage"),
        ):
            runway.generate_from_runway(
                "fox", "images/", duration=20, video_format="SQUARE"
            )
        body = request.call_args_list[0].kwargs["body"]
        self.assertTrue(request.call_args_list[0].args[1].endswith("/text_to_video"))
        self.assertEqual(body["ratio"], "1280:720")
        self.assertEqual(body["duration"], 10)
        self.assertNotIn("promptImage", body)

    def test_runway_rejects_long_utf16_prompt_before_spending(self):
        with (
            patch.object(http, "json_request") as request,
            self.assertRaisesRegex(APIException, "1,000"),
        ):
            runway.generate_from_runway("🦊" * 500, "images/")
        request.assert_not_called()

    def test_runway_failed_job_does_not_download(self):
        with (
            patch.object(
                http,
                "json_request",
                side_effect=[
                    {"id": "task"},
                    {"status": "FAILED"},
                ],
            ),
            self.assertRaises(APIException),
        ):
            runway.generate_from_runway("fox", "images/")
        self.save_download.assert_not_called()

    def gemini_result(self, output):
        return {
            "status": "completed",
            "steps": [
                {
                    "type": "user_input",
                    "content": [{"type": "video", "uri": "ignored"}],
                },
                {"type": "model_output", "content": [output]},
            ],
        }

    def test_gemini_reads_rest_steps_and_polls_file(self):
        response = self.gemini_result(
            {
                "type": "video",
                "uri": "https://generativelanguage.googleapis.com/v1beta/files/abc:download?alt=media",
            }
        )
        with (
            patch.object(
                http,
                "json_request",
                side_effect=[
                    response,
                    {"state": "PROCESSING"},
                    {"state": "ACTIVE"},
                ],
            ) as request,
            patch.object(gemini_video, "video_metadata", return_value={"duration": 8}),
            patch.object(gemini_video, "record_usage") as usage,
        ):
            gemini_video.generate_from_gemini_video(
                "fox", "images/", reference="ref.png", video_format="PORTRAIT"
            )
        body = request.call_args_list[0].kwargs["body"]
        self.assertEqual(body["response_format"]["aspect_ratio"], "9:16")
        self.assertEqual(body["input"][0]["type"], "image")
        self.assertFalse(body["store"])
        self.assertEqual(
            self.save_download.call_args.kwargs["auth_host"], gemini_video.HOST
        )
        self.assertEqual(usage.call_args.kwargs["seconds"], 8)

    def test_gemini_supports_inline_output(self):
        self.image_data.return_value = None
        response = self.gemini_result(
            {"type": "video", "data": base64.b64encode(b"video").decode()}
        )
        with (
            patch.object(http, "json_request", return_value=response),
            patch.object(http, "save_stream", return_value="a.mp4") as save,
            patch.object(
                gemini_video, "video_metadata", return_value={"duration": 6.2}
            ),
            patch.object(gemini_video, "record_usage") as usage,
        ):
            self.assertEqual(
                gemini_video.generate_from_gemini_video("fox", "images/"), "a.mp4"
            )
        self.assertEqual(save.call_args.args[0].getvalue(), b"video")
        self.assertEqual(usage.call_args.kwargs["seconds"], 7)

    def test_gemini_rejects_foreign_authenticated_download(self):
        response = self.gemini_result(
            {"type": "video", "uri": "https://evil.example/files/a"}
        )
        with (
            patch.object(http, "json_request", return_value=response),
            self.assertRaises(APIException),
        ):
            gemini_video.generate_from_gemini_video("fox", "images/")
        self.save_download.assert_not_called()

    def test_gemini_requires_model_video_output(self):
        with self.assertRaises(APIException):
            gemini_video.video_output(
                {"steps": [{"type": "user_input", "content": [{"type": "video"}]}]}
            )


class VideoHTTPTests(SimpleTestCase):
    def test_reference_normalizes_image_and_preserves_orientation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "ref.png")
            Image.new("RGBA", (2000, 1000)).save(path)
            data = http.image_data(path)
        with Image.open(BytesIO(base64.b64decode(data))) as result:
            self.assertEqual(result.mode, "RGB")
            self.assertEqual(result.size, (1536, 768))

    @override_settings(VIDEO_GENERATION_TIMEOUT=0, VIDEO_POLL_INTERVAL=0)
    def test_polling_has_a_deadline_and_warns_before_retrying(self):
        fetch = MagicMock()
        with self.assertRaisesRegex(APIException, "may still finish and charge"):
            http.poll(fetch, completed={"DONE"}, pending={"WAIT"}, label="Test")
        fetch.assert_not_called()

    def test_transport_errors_never_expose_key_or_url(self):
        call = http.guarded("Test")(
            lambda: (_ for _ in ()).throw(
                requests.RequestException("secret-key signed-url")
            )
        )
        with self.assertRaises(APIException) as caught:
            call()
        self.assertNotIn("secret-key", str(caught.exception))
        self.assertNotIn("signed-url", str(caught.exception))

    def test_json_requests_block_redirects_and_sanitize_http_errors(self):
        response = MagicMock(status_code=401)
        with patch.object(http.requests, "request") as request:
            request.return_value.__enter__.return_value = response
            with self.assertRaisesRegex(APIException, "HTTP 401"):
                http.json_request(
                    "POST", "https://api.example/", headers={"Authorization": "secret"}
                )
        self.assertFalse(request.call_args.kwargs["allow_redirects"])

    def test_partial_normalized_output_is_removed_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:

            def fail(stream, path):
                Path(path).write_bytes(b"partial")
                raise ValueError("bad video")

            with (
                patch.object(http, "save_video", side_effect=fail),
                self.assertRaises(ValueError),
            ):
                http.save_stream(BytesIO(b"bad"), directory)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_download_credentials_are_scoped_to_google(self):
        with patch.object(http.requests, "get") as get, self.assertRaises(APIException):
            http.save_download(
                "https://evil.example/file",
                "/tmp",
                headers={"x-goog-api-key": "secret"},
                auth_host=gemini_video.HOST,
            )
        get.assert_not_called()

    def test_google_download_redirect_does_not_forward_key_to_cdn(self):
        redirect = MagicMock(
            status_code=302, headers={"Location": "https://cdn.example/result.mp4"}
        )
        complete = MagicMock(status_code=200)
        complete.iter_content.return_value = [b"video"]
        first, second = MagicMock(), MagicMock()
        first.__enter__.return_value = redirect
        second.__enter__.return_value = complete
        with (
            patch.object(http.requests, "get", side_effect=[first, second]) as get,
            patch.object(http, "save_stream", return_value="saved.mp4"),
        ):
            result = http.save_download(
                "https://generativelanguage.googleapis.com/v1beta/files/abc:download",
                "/tmp",
                headers={"x-goog-api-key": "secret"},
                auth_host=gemini_video.HOST,
            )
        self.assertEqual(result, "saved.mp4")
        self.assertEqual(
            get.call_args_list[0].kwargs["headers"], {"x-goog-api-key": "secret"}
        )
        self.assertEqual(get.call_args_list[1].kwargs["headers"], {})
        self.assertFalse(get.call_args_list[1].kwargs["allow_redirects"])

    def test_download_size_limit(self):
        response = MagicMock(status_code=200)
        response.iter_content.return_value = [b"12345"]
        with (
            patch.object(http.requests, "get") as get,
            patch.object(http, "MAX_VIDEO_BYTES", 4),
        ):
            get.return_value.__enter__.return_value = response
            with self.assertRaisesRegex(APIException, "download limit"):
                http.save_download("https://cdn.example/file.mp4", "/tmp")


class VideoKeyTests(TestCase):
    @override_settings(FAL_KEY="service-fal", RUNWAY_API_KEY="service-runway")
    def test_new_encrypted_keys_follow_service_personal_selection_and_are_masked(self):
        keys = api_keys.make(
            fal_key="personal-fal-secret", runway_key="personal-runway-secret"
        )
        for provider, expected in (
            (Provider.FAL, "service-fal"),
            (Provider.RUNWAY, "service-runway"),
        ):
            self.assertEqual(ApiKeys.key_for(keys.user, provider), expected)
        keys.user.use_service_api_keys = False
        keys.user.save(update_fields=["use_service_api_keys"])
        self.assertEqual(ApiKeys.key_for(keys.user, Provider.FAL), keys.fal_key)
        self.assertEqual(ApiKeys.key_for(keys.user, Provider.RUNWAY), keys.runway_key)
        data = ApiKeysSerializer(keys).data
        self.assertNotEqual(data["fal_key"], keys.fal_key)
        self.assertNotEqual(data["runway_key"], keys.runway_key)

    @override_settings(FAL_KEY="service-fal")
    def test_missing_personal_key_never_falls_back_to_service(self):
        keys = api_keys.make(fal_key="")
        keys.user.use_service_api_keys = False
        keys.user.save(update_fields=["use_service_api_keys"])
        self.assertIsNone(ApiKeys.key_for(keys.user, Provider.FAL))
        with self.assertRaisesRegex(APIException, "API key"):
            http.key_for(keys.user, Provider.FAL)
