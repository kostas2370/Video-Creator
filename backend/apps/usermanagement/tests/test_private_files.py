import importlib

from django.test import SimpleTestCase, override_settings
from django.urls import Resolver404, clear_url_caches, resolve

from video_creator import urls


class PrivateFileRouteTests(SimpleTestCase):
    def test_development_media_route_cannot_serve_backend_files(self):
        try:
            with override_settings(DEBUG=True):
                importlib.reload(urls)
                clear_url_caches()
                for path in ("/.env", "/db.sqlite3", "/video_creator/settings/base.py"):
                    with self.subTest(path=path), self.assertRaises(Resolver404):
                        resolve(path)
                match = resolve("/media/example.mp4")
                self.assertEqual(
                    match.kwargs["document_root"], urls.settings.BASE_DIR / "media"
                )
                self.assertEqual(self.client.get("/media/../.env").status_code, 400)
        finally:
            importlib.reload(urls)
            clear_url_caches()
