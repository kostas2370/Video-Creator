import io
import json
import tempfile
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.videomanagement.management.commands.download_icons import svg_artwork
from apps.videomanagement.models import Icon
from apps.videomanagement.serializers.diagrams import DiagramItemSerializer
from apps.videomanagement.services.media.icons import icon_candidates

from .base import ApiTestCase


COLLECTION = {
    "prefix": "lucide", "width": 24, "height": 24,
    "info": {"license": {"title": "ISC", "spdx": "ISC", "url": "https://lucide.dev/license"}, "author": {"name": "Lucide"}},
    "icons": {
        "droplet": {"body": '<path d="M12 2 L20 20 L4 20 Z" fill="currentColor"/>'},
        "cloud": {"body": '<path d="M2 12 L22 12" stroke="currentColor"/>'},
        "unsafe": {"body": '<image href="https://example.com/image.svg"/>'},
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

    def test_import_is_repeatable_keeps_licenses_and_rejects_active_svg(self):
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
        for body in ('<script>alert(1)</script>', '<path onclick="alert(1)"/>', '<path fill="url(https://example.com/x)"/>'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                svg_artwork({"body": body}, COLLECTION)

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
