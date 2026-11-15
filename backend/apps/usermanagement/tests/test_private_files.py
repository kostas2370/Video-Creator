from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from apps.videomanagement.protected_media import protected_media


class PrivateFileRouteTests(SimpleTestCase):
    def test_backend_files_have_no_static_route(self):
        for path in ("/.env", "/db.sqlite3", "/video_creator/settings/base.py"):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)

    def test_media_always_uses_the_authenticated_view(self):
        self.assertEqual(resolve("/media/example.mp4").func, protected_media)
