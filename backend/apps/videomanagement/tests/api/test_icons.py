import io
import json
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.usermanagement.baker_recipes import user

from apps.videomanagement.models import Icon
from apps.videomanagement.serializers.diagrams import DiagramItemSerializer
from apps.videomanagement.services.media.icons import icon_candidates, available_icon_files
from apps.videomanagement.serializers.overlays import OverlaySerializer
from apps.videomanagement.services.scenes.narration import ensure_scene_rows

from .base import ApiTestCase


COLLECTION = {
    "prefix": "lucide", "width": 24, "height": 24,
    "info": {"license": {"title": "ISC", "spdx": "ISC", "url": "https://lucide.dev/license"}, "author": {"name": "Lucide"}},
    "icons": {
        "droplet": {"body": '<path d="M12 2 L20 20 L4 20 Z" fill="currentColor"/>'},
        "cloud": {"body": '<path d="M2 12 L22 12" stroke="currentColor"/>'},
        "hidden": {"body": '<path d="M0 0"/>', "hidden": True},
    },
    "categories": {"Weather": ["droplet", "cloud"]},
}


class IconCatalogTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        override = override_settings(MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)

    def download(self):
        with patch("apps.videomanagement.management.commands.download_icons.download", side_effect=[json.dumps(COLLECTION).encode(), b"ISC license notice"]):
            call_command("download_icons", collections=["lucide"], stdout=io.StringIO())

    def test_import_is_repeatable_keeps_licenses_and_skips_hidden_icons(self):
        self.download()
        self.assertEqual(Icon.objects.count(), 2)
        icon = Icon.objects.get(pk="lucide:droplet")
        filename = icon.file.name
        with icon.file.open("rb") as artwork:
            self.assertIn(b"#ffffff", artwork.read())
        from django.core.files.storage import default_storage
        with default_storage.open("media/icons/lucide/LICENSE.txt", "rb") as notice:
            self.assertEqual(notice.read(), b"ISC license notice")
        icon.enabled = False
        icon.save()
        self.download()
        icon.refresh_from_db()
        self.assertEqual(Icon.objects.count(), 2)
        self.assertEqual(icon.file.name, filename)
        self.assertFalse(icon.enabled)

    def test_authenticated_search_pagination_and_exact_id_lookup(self):
        self.download()
        Icon.objects.bulk_create([Icon(key=f"mdi:test-{i}", collection="mdi", name=f"Test {i:02}", file="media/icons/test.svg") for i in range(30)])
        first = self.client.get(reverse("icons"))
        second = self.client.get(reverse("icons"), {"page": 2})
        self.assertEqual(first.data["count"], 32)
        self.assertEqual(len(first.data["results"]), 24)
        self.assertFalse({row["key"] for row in first.data["results"]} & {row["key"] for row in second.data["results"]})
        result = self.client.get(reverse("icons"), {"search": "droplets"}).data
        self.assertEqual([row["key"] for row in result["results"]], ["lucide:droplet"])
        self.assertIn("http://testserver/", result["results"][0]["file"])
        self.assertEqual(self.client.get(reverse("icons"), {"keys": "lucide:cloud"}).data["count"], 1)
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(reverse("icons")).status_code, (401, 403))

    def test_shortlist_and_validation_exclude_unknown_disabled_or_missing_files(self):
        self.download()
        self.assertEqual(icon_candidates("droplet", limit=1)[0]["id"], "lucide:droplet")
        self.assertEqual(icon_candidates("droplet", limit=0), [])
        for key, expected in (("lucide:droplet", "lucide:droplet"), ("unknown:x", ""), ("../../etc/passwd", "")):
            item = DiagramItemSerializer(data={"label": "Rain", "icon": key})
            item.is_valid(raise_exception=True)
            self.assertEqual(item.validated_data["icon"], expected)
        icon = Icon.objects.get(pk="lucide:droplet")
        icon.file.delete(save=False)
        self.assertNotIn("lucide:droplet", {row["id"] for row in icon_candidates("droplet")})
        item = DiagramItemSerializer(data={"label": "Rain", "icon": "lucide:droplet"})
        item.is_valid(raise_exception=True)
        self.assertEqual(item.validated_data["icon"], "")

    def test_search_ignores_common_words_and_matches_word_boundaries(self):
        Icon.objects.bulk_create([
            Icon(key="mdi:pinterest", collection="mdi", name="Pinterest", file="pin.svg"),
            Icon(key="mdi:bank", collection="mdi", name="Bank", file="bank.svg"),
            Icon(key="mdi:ampersand", collection="mdi", name="Ampersand", file="and.svg"),
        ])
        result = self.client.get(reverse("icons"), {"search": "interest and bank"})
        self.assertEqual([row["key"] for row in result.data["results"]], ["mdi:bank"])

    def upload(self, **changes):
        buffer = io.BytesIO()
        Image.new("RGBA", (80, 40), (200, 30, 40, 128)).save(buffer, format="PNG")
        return self.client.post(reverse("icons"), {
            "name": "Custom engine", "description": "Engine combustion", "file": SimpleUploadedFile("engine.png", buffer.getvalue(), content_type="image/png"),
            **changes,
        }, format="multipart")

    def test_upload_normalizes_without_distortion_and_forces_owner_and_generated_id(self):
        response = self.upload(key="lucide:cloud", collection="lucide", created_by=str(user.make().pk))
        self.assertEqual(response.status_code, 201, response.data)
        icon = Icon.objects.get(pk=response.data["key"])
        self.assertTrue(icon.key.startswith("custom:"))
        self.assertEqual(icon.collection, "custom")
        self.assertEqual(icon.created_by, self.user)
        with icon.file.open("rb") as source, Image.open(source) as image:
            self.assertEqual(image.size, (256, 256))
            self.assertEqual(image.getbbox(), (0, 64, 256, 192))
            for actual, expected in zip(image.getpixel((128, 128)), (200, 30, 40, 128)):
                self.assertAlmostEqual(actual, expected, delta=1)
            self.assertEqual(image.getpixel((0, 0))[3], 0)
        self.assertIn(icon.key, available_icon_files([icon.key], user=self.user))
        self.assertIn(icon.key, {row["id"] for row in icon_candidates("engine", user=self.user)})

    def test_other_users_cannot_discover_select_or_plan_uploaded_icons(self):
        response = self.upload()
        key = response.data["key"]
        other = user.make()
        self.client.force_authenticate(other)
        for query in ({}, {"keys": key}, {"search": "engine"}):
            result = self.client.get(reverse("icons"), query)
            self.assertNotIn(key, {row["key"] for row in result.data["results"]})
        self.assertNotIn(key, available_icon_files([key], user=other))
        self.assertNotIn(key, {row["id"] for row in icon_candidates("engine", user=other)})
        item = DiagramItemSerializer(data={"label": "Engine", "icon": key}, context={"user": other})
        item.is_valid(raise_exception=True)
        self.assertEqual(item.validated_data["icon"], "")

    def test_uploaded_icon_survives_scene_save_storyboard_application_and_preview(self):
        key = self.upload().data["key"]
        diagram = {"template": "graph", "items": [{"label": "Engine", "icon": key}, {"label": "Power"}]}
        editing = {"motion_style": "NONE", "motion_intensity": "SUBTLE", "transition_after": "CUT", "transition_duration": .1, "pause_after": 0, "diagram": diagram}
        video = self.video_for(mode="WEB", status="READY", settings={"ai_scene_editing": True}, gpt_answer={"title": "Engine", "scenes": [{"scene": "Engine", "sentences": [{"sentence": "An engine makes power.", "image_description": "engine", "editing": editing}]}]})
        ensure_scene_rows(video)
        scene = video.scenes.get()
        self.assertEqual(scene.overlays[0]["diagram"]["items"][0]["icon"], key)
        response = self.client.patch(reverse("scene-overlays", args=[scene.pk]), {"overlays": scene.overlays}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        preview = self.client.get(reverse("video-preview", args=[video.pk]))
        self.assertEqual(preview.data["segments"][0]["overlays"][0]["diagram"]["items"][0]["icon"], key)
        overlay = OverlaySerializer(data={"kind": "diagram", "diagram": diagram}, context={"user": self.user})
        overlay.is_valid(raise_exception=True)
        self.assertEqual(overlay.validated_data["diagram"]["items"][0]["icon"], key)

    def test_upload_rejects_invalid_oversized_and_animated_artwork(self):
        for file in (
            SimpleUploadedFile("bad.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>', content_type="image/svg+xml"),
            SimpleUploadedFile("broken.png", b"not an image", content_type="image/png"),
        ):
            self.assertEqual(self.upload(file=file).status_code, 400)
        for image, options in ((Image.new("RGB", (2001, 2000)), {}), (Image.new("RGBA", (10, 10)), {"save_all": True, "append_images": [Image.new("RGBA", (10, 10), "red")], "duration": 100})):
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", **options)
            response = self.upload(file=SimpleUploadedFile("image.png", buffer.getvalue(), content_type="image/png"))
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Icon.objects.count(), 0)
        self.client.force_authenticate(None)
        self.assertIn(self.upload().status_code, (401, 403))
