from django.test import SimpleTestCase, override_settings


@override_settings(DEBUG=False, ROOT_URLCONF="video_creator.static_assets")
class FrameworkStaticFilesTests(SimpleTestCase):
    def test_admin_css_is_available_without_collected_static_files(self):
        response = self.client.get("/static/admin/css/base.css")
        self.addCleanup(response.close)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/css")
        self.assertIn(b"--primary", b"".join(response.streaming_content))

    def test_private_and_unrelated_files_are_not_exposed(self):
        for url in (
            "/static/admin/",
            "/static/admin/.env",
            "/static/media/private.jpg",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)
