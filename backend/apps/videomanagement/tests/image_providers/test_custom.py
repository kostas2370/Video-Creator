import io
import os
import subprocess
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import requests
from PIL import Image
from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from apps.apikeysmanagement.models import UserCustomVisualProvider
from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, video
from ...utils.image_providers import ImageProviderRegistry, custom, resolve
from ...utils.scenes import create_image_scene, generate_new_image
from ...baker_recipes import scene_image


def image_bytes(format="PNG", mode="RGB"):
    buffer = io.BytesIO()
    with Image.new(mode, (3, 2), "red") as image:
        image.save(buffer, format=format)
    return buffer.getvalue()


def response(body=None, content_type="image/png", payload=None):
    result = MagicMock()
    result.__enter__.return_value = result
    result.headers = {"Content-Type": content_type}
    result.iter_content.return_value = [body if body is not None else image_bytes()]
    result.json.return_value = payload
    return result


class CustomImageProviderTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.provider = UserCustomVisualProvider.objects.create(
            user=self.user,
            name="Studio images",
            output_type="IMAGE",
            endpoint_url="https://example.com/generate",
            auth_type="bearer",
            api_key="private-secret",
            prompt_field_name="description",
        )
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def generate(self, **kwargs):
        return custom.generate_from_custom_provider(
            "a red house",
            self.directory,
            user=kwargs.pop("user", self.user),
            provider_name=kwargs.pop("provider_name", self.provider.name),
            **kwargs,
        )

    def assert_png(self, path):
        self.assertEqual(os.path.dirname(path), self.directory)
        self.assertTrue(path.endswith(".png"))
        with Image.open(path) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (3, 2))
            image.verify()

    def test_posts_the_configured_prompt_field_and_bearer_credential(self):
        result = response()
        with patch.object(custom.requests, "post", return_value=result) as post:
            path = self.generate(style="vivid", title="Title")
        self.assert_png(path)
        post.assert_called_once_with(
            self.provider.endpoint_url,
            json={"description": "a red house"},
            headers={
                "Accept": "image/*, application/json",
                "Content-Type": "application/json",
                "Authorization": "Bearer private-secret",
            },
            auth=None,
            timeout=30,
            stream=True,
            allow_redirects=False,
        )
        result.__exit__.assert_called_once()

    def test_extra_parameters_are_merged_without_replacing_the_prompt(self):
        parameters = {
            "model": "custom-model",
            "description": "wrong",
            "options": {"seed": 3},
        }
        self.provider.extra_parameters = parameters
        self.provider.save()
        with patch.object(custom.requests, "post", return_value=response()) as post:
            self.assert_png(self.generate())
        self.assertEqual(
            post.call_args.kwargs["json"],
            {
                "model": "custom-model",
                "description": "a red house",
                "options": {"seed": 3},
            },
        )
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.extra_parameters, parameters)

    def test_supports_header_basic_and_no_authentication(self):
        for auth_type in ("header", "basic", "none"):
            with self.subTest(auth_type=auth_type):
                self.provider.auth_type = auth_type
                self.provider.auth_header_name = "x-api-key"
                self.provider.api_key = "username:password"
                self.provider.save()
                with patch.object(
                    custom.requests, "post", return_value=response()
                ) as post:
                    self.assert_png(self.generate())
                kwargs = post.call_args.kwargs
                if auth_type == "header":
                    self.assertEqual(
                        kwargs["headers"]["x-api-key"], "username:password"
                    )
                    self.assertIsNone(kwargs["auth"])
                elif auth_type == "basic":
                    self.assertEqual(
                        (kwargs["auth"].username, kwargs["auth"].password),
                        ("username", "password"),
                    )
                else:
                    self.assertNotIn("Authorization", kwargs["headers"])
                    self.assertNotIn("x-api-key", kwargs["headers"])
                    self.assertIsNone(kwargs["auth"])

    def test_downloads_supported_json_url_responses_without_forwarding_credentials(
        self,
    ):
        for payload in (
            {"url": "https://cdn.example.com/image.png"},
            {"image_url": "https://cdn.example.com/image.png"},
            {"data": [{"url": "https://cdn.example.com/image.png"}]},
        ):
            with self.subTest(payload=payload):
                generated = response(
                    content_type="application/json; charset=utf-8", payload=payload
                )
                downloaded = response()
                with (
                    patch.object(custom.requests, "post", return_value=generated),
                    patch.object(
                        custom.requests, "get", return_value=downloaded
                    ) as get,
                ):
                    self.assert_png(self.generate())
                get.assert_called_once_with(
                    "https://cdn.example.com/image.png", timeout=30, stream=True
                )
                generated.__exit__.assert_called_once()
                downloaded.__exit__.assert_called_once()

    def test_normalizes_jpeg_and_webp_images_to_renderable_png(self):
        for format in ("JPEG", "WEBP"):
            with self.subTest(format=format):
                with patch.object(
                    custom.requests,
                    "post",
                    return_value=response(body=image_bytes(format)),
                ):
                    self.assert_png(self.generate())

    def test_preserves_image_transparency(self):
        with patch.object(
            custom.requests,
            "post",
            return_value=response(body=image_bytes(mode="RGBA")),
        ):
            path = self.generate()
        with Image.open(path) as image:
            self.assertEqual(image.mode, "RGBA")

    def test_saves_unique_filenames_for_repeated_requests(self):
        with patch.object(
            custom.requests, "post", side_effect=[response(), response()]
        ):
            first, second = self.generate(), self.generate()
        self.assertNotEqual(first, second)
        self.assert_png(first)
        self.assert_png(second)

    def test_streams_chunks_and_skips_empty_chunks(self):
        raw = image_bytes()
        result = response()
        result.iter_content.return_value = [raw[:10], b"", raw[10:]]
        with patch.object(custom.requests, "post", return_value=result):
            self.assert_png(self.generate())

    def test_rejects_missing_and_foreign_provider_names_before_making_requests(self):
        for owner, name in (
            (None, self.provider.name),
            (user.make(), self.provider.name),
            (self.user, "missing"),
            (self.user, None),
        ):
            with self.subTest(owner=owner, name=name):
                with patch.object(custom.requests, "post") as post:
                    with self.assertRaises(NotFound):
                        self.generate(user=owner, provider_name=name)
                post.assert_not_called()

    def test_identical_names_are_resolved_using_the_caller(self):
        other_user = user.make()
        UserCustomVisualProvider.objects.create(
            user=other_user,
            name=self.provider.name,
            output_type="IMAGE",
            endpoint_url="https://other.example.com/images",
            auth_type="none",
        )
        with patch.object(custom.requests, "post", return_value=response()) as post:
            self.assert_png(self.generate(user=other_user))
        self.assertEqual(post.call_args.args[0], "https://other.example.com/images")
        self.assertNotIn("Authorization", post.call_args.kwargs["headers"])

    def test_invalid_output_types_are_rejected_before_making_requests(self):
        UserCustomVisualProvider.objects.filter(pk=self.provider.pk).update(
            output_type="INVALID"
        )
        with patch.object(custom.requests, "post") as post:
            with self.assertRaises(ValidationError):
                self.generate()
        post.assert_not_called()

    def test_timeouts_do_not_leave_files(self):
        with patch.object(custom.requests, "post", side_effect=requests.Timeout):
            self.assertIsNone(self.generate())
        self.assertEqual(os.listdir(self.directory), [])

    def test_http_errors_do_not_save_the_response_body(self):
        result = response()
        result.raise_for_status.side_effect = requests.HTTPError("provider refused")
        with patch.object(custom.requests, "post", return_value=result):
            self.assertIsNone(self.generate())
        self.assertEqual(os.listdir(self.directory), [])
        result.iter_content.assert_not_called()
        result.__exit__.assert_called_once()

    def test_empty_and_invalid_image_bytes_leave_no_files(self):
        for body in (b"", b"not an image"):
            with self.subTest(body=body):
                with patch.object(
                    custom.requests, "post", return_value=response(body=body)
                ):
                    self.assertIsNone(self.generate())
                self.assertEqual(os.listdir(self.directory), [])

    def test_invalid_json_and_non_http_urls_are_not_downloaded(self):
        for payload in (
            {},
            {"id": "pending-job"},
            [],
            {"url": "file:///etc/passwd"},
            {"url": "relative.png"},
        ):
            with self.subTest(payload=payload):
                with (
                    patch.object(
                        custom.requests,
                        "post",
                        return_value=response(
                            content_type="application/json", payload=payload
                        ),
                    ),
                    patch.object(custom.requests, "get") as get,
                ):
                    self.assertIsNone(self.generate())
                get.assert_not_called()
                self.assertEqual(os.listdir(self.directory), [])

    def test_download_failure_leaves_no_partial_image(self):
        download = response()

        def broken_stream(*args, **kwargs):
            yield image_bytes()[:10]
            raise requests.ConnectionError("disconnected")

        download.iter_content.side_effect = broken_stream
        with (
            patch.object(
                custom.requests,
                "post",
                return_value=response(
                    content_type="application/json",
                    payload={"url": "https://cdn.example.com/a.png"},
                ),
            ),
            patch.object(custom.requests, "get", return_value=download),
        ):
            self.assertIsNone(self.generate())
        self.assertEqual(os.listdir(self.directory), [])
        download.__exit__.assert_called_once()

    def test_failure_during_saving_removes_partial_output(self):
        def fail_save(image, path, **kwargs):
            with open(path, "wb") as file:
                file.write(b"partial")
            raise OSError("disk full")

        with (
            patch.object(custom.requests, "post", return_value=response()),
            patch.object(Image.Image, "save", autospec=True, side_effect=fail_save),
        ):
            self.assertIsNone(self.generate())
        self.assertEqual(os.listdir(self.directory), [])

    def test_error_logs_do_not_expose_request_secrets(self):
        with patch.object(
            custom.requests, "post", side_effect=requests.HTTPError("private-secret")
        ):
            with self.assertLogs(custom.logger, level="ERROR") as logs:
                self.assertIsNone(self.generate())
        self.assertNotIn("private-secret", " ".join(logs.output))

    def test_registry_routes_custom_names_to_the_retrieval_function(self):
        with patch.object(
            custom, "generate_from_custom_provider", return_value="image.png"
        ) as generate:
            result = resolve("AI", self.provider.name)(
                "a cat", self.directory, user=self.user
            )
        self.assertEqual(result, "image.png")
        generate.assert_called_once_with(
            "a cat", self.directory, user=self.user, provider_name=self.provider.name
        )

    def test_scene_generation_saves_custom_image_result(self):
        row = video.make(created_by=self.user)
        line = scene.make(video=row, text="a red house")
        with patch.object(custom.requests, "post", return_value=response()):
            path = create_image_scene(
                row,
                "a red house",
                line.text,
                self.directory,
                mode="AI",
                provider=self.provider.name,
                user=self.user,
            )
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(line.scene_images.get().file.name, path)

    def test_scene_regeneration_uses_the_owners_custom_provider(self):
        row = video.make(
            created_by=self.user,
            mode="AI",
            dir_name=self.directory,
            settings={"provider": self.provider.name},
        )
        image = scene_image.make(scene=scene.make(video=row))
        with patch.object(custom.requests, "post", return_value=response()):
            generate_new_image(image, row)
        image.refresh_from_db()
        self.assertTrue(os.path.isfile(image.file.name))


class CustomVideoProviderTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with tempfile.TemporaryDirectory() as directory:
            cls.clips = {}
            for extension, codec in (("mp4", "libx264"), ("webm", "libvpx")):
                path = os.path.join(directory, "clip." + extension)
                subprocess.run(
                    [
                        custom.get_setting("FFMPEG_BINARY"),
                        "-nostdin",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        "color=c=red:s=32x24:r=10",
                        "-f",
                        "lavfi",
                        "-i",
                        "sine=frequency=440:sample_rate=44100",
                        "-t",
                        "0.5",
                        "-c:v",
                        codec,
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac" if extension == "mp4" else "libvorbis",
                        path,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
                cls.clips[extension] = Path(path).read_bytes()

    def setUp(self):
        self.user = user.make()
        self.provider = UserCustomVisualProvider.objects.create(
            user=self.user,
            name="Studio videos",
            output_type="VIDEO",
            endpoint_url="https://example.com/video",
            auth_type="header",
            auth_header_name="x-api-key",
            api_key="private-secret",
            prompt_field_name="description",
            extra_parameters={
                "model": "cinematic",
                "description": "wrong",
                "options": {"seed": 12},
            },
        )
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def generate(self, owner=None):
        return resolve("AI", self.provider.name)(
            "a moving red house", self.directory, user=owner or self.user
        )

    def video_response(self, extension="mp4"):
        return response(self.clips[extension], content_type="video/" + extension)

    def assert_video(self, path):
        self.assertTrue(path.endswith(".mp4"))
        with custom.VideoFileClip(path) as clip:
            self.assertGreater(clip.duration, 0)
            self.assertEqual(clip.size, [32, 24])
            self.assertIsNotNone(clip.audio)
            self.assertEqual(clip.get_frame(0).shape, (24, 32, 3))

    def test_raw_video_uses_configured_authentication_parameters_and_timeout(self):
        result = self.video_response()
        with patch.object(custom.requests, "post", return_value=result) as post:
            path = self.generate()
        self.assert_video(path)
        post.assert_called_once_with(
            self.provider.endpoint_url,
            json={
                "description": "a moving red house",
                "model": "cinematic",
                "options": {"seed": 12},
            },
            headers={
                "Accept": "video/*, application/json",
                "Content-Type": "application/json",
                "x-api-key": "private-secret",
            },
            auth=None,
            timeout=300,
            stream=True,
            allow_redirects=False,
        )
        result.__exit__.assert_called_once()

    def test_video_urls_are_downloaded_without_provider_credentials(self):
        for payload in (
            {"url": "https://cdn.example.com/video.mp4"},
            {"video_url": "https://cdn.example.com/video.mp4"},
            {"data": [{"url": "https://cdn.example.com/video.mp4"}]},
            {"data": [{"video_url": "https://cdn.example.com/video.mp4"}]},
        ):
            with self.subTest(payload=payload):
                generated = response(content_type="application/json", payload=payload)
                downloaded = self.video_response()
                with (
                    patch.object(custom.requests, "post", return_value=generated),
                    patch.object(
                        custom.requests, "get", return_value=downloaded
                    ) as get,
                ):
                    self.assert_video(self.generate())
                get.assert_called_once_with(
                    "https://cdn.example.com/video.mp4", timeout=300, stream=True
                )
                generated.__exit__.assert_called_once()
                downloaded.__exit__.assert_called_once()

    def test_webm_is_transcoded_into_an_mp4_with_audio(self):
        with patch.object(
            custom.requests, "post", return_value=self.video_response("webm")
        ):
            path = self.generate()
        self.assert_video(path)
        self.assertIn(b"ftyp", Path(path).read_bytes()[:32])

    def test_invalid_and_image_responses_leave_no_video_files(self):
        for body in (b"", b"invalid video", image_bytes()):
            with self.subTest(body=body[:20]):
                with patch.object(
                    custom.requests, "post", return_value=response(body, "video/mp4")
                ):
                    self.assertIsNone(self.generate())
                self.assertEqual(os.listdir(self.directory), [])

    def test_foreign_video_provider_is_rejected_before_the_request(self):
        with patch.object(custom.requests, "post") as post:
            with self.assertRaises(NotFound):
                self.generate(owner=user.make())
        post.assert_not_called()

    def test_interrupted_download_leaves_no_partial_video(self):
        result = self.video_response()

        def interrupted(*args, **kwargs):
            yield self.clips["mp4"][:20]
            raise requests.ConnectionError("disconnected")

        result.iter_content.side_effect = interrupted
        with patch.object(custom.requests, "post", return_value=result):
            self.assertIsNone(self.generate())
        self.assertEqual(os.listdir(self.directory), [])
        result.__exit__.assert_called_once()

    def test_job_only_and_invalid_url_responses_are_not_saved(self):
        for payload in (
            {"id": "pending-job"},
            {"video_url": "file:///a.mp4"},
            {"image_url": "https://cdn.example.com/a.png"},
        ):
            with self.subTest(payload=payload):
                with (
                    patch.object(
                        custom.requests,
                        "post",
                        return_value=response(
                            content_type="application/json", payload=payload
                        ),
                    ),
                    patch.object(custom.requests, "get") as get,
                ):
                    self.assertIsNone(self.generate())
                get.assert_not_called()
                self.assertEqual(os.listdir(self.directory), [])

    def test_transcoding_errors_and_timeouts_remove_partial_output(self):
        for failure in (
            subprocess.CalledProcessError(1, "ffmpeg"),
            subprocess.TimeoutExpired("ffmpeg", 300),
        ):
            with self.subTest(failure=failure):

                def fail_transcode(args, **kwargs):
                    Path(args[-1]).write_bytes(b"partial")
                    raise failure

                with (
                    patch.object(
                        custom.requests, "post", return_value=self.video_response()
                    ),
                    patch.object(custom.subprocess, "run", side_effect=fail_transcode),
                ):
                    self.assertIsNone(self.generate())
                self.assertEqual(os.listdir(self.directory), [])

    def test_video_metadata_is_scoped_to_the_owner(self):
        self.assertTrue(ImageProviderRegistry.is_video(self.provider.name, self.user))
        self.assertFalse(
            ImageProviderRegistry.is_video(self.provider.name, user.make())
        )
        self.assertFalse(ImageProviderRegistry.is_video(self.provider.name))
        self.assertTrue(ImageProviderRegistry.is_video("sora"))
        self.assertFalse(ImageProviderRegistry.is_video("DALL-E", self.user))

    def test_scene_generation_saves_video_and_enables_its_audio(self):
        row = video.make(created_by=self.user)
        line = scene.make(video=row, text="a red house")
        with patch.object(custom.requests, "post", return_value=self.video_response()):
            path = create_image_scene(
                row,
                "a moving red house",
                line.text,
                self.directory,
                mode="AI",
                provider=self.provider.name,
                user=self.user,
                with_audio=True,
            )
        self.assert_video(path)
        visual = line.scene_images.get()
        self.assertEqual(visual.file.name, path)
        self.assertTrue(visual.with_audio)

    def test_scene_regeneration_saves_the_video_and_retains_it_on_failure(self):
        row = video.make(
            created_by=self.user,
            mode="AI",
            dir_name=self.directory,
            settings={"provider": self.provider.name},
        )
        visual = scene_image.make(scene=scene.make(video=row))
        with patch.object(custom.requests, "post", return_value=self.video_response()):
            generate_new_image(visual, row)
        visual.refresh_from_db()
        self.assert_video(visual.file.name)
        previous = visual.file.name
        with patch.object(custom.requests, "post", side_effect=requests.Timeout):
            generate_new_image(visual, row)
        visual.refresh_from_db()
        self.assertEqual(visual.file.name, previous)
