import os
import runpy
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.videomanagement.baker_recipes import intro, scene, video

from ..baker_recipes import user


class SecretConfigurationTests(SimpleTestCase):
    def test_missing_blank_and_retired_secrets_fail_startup(self):
        base = settings.BASE_DIR / "video_creator/settings/base.py"
        for value in (None, "", "   ", "REMOVED_EXPOSED_CREDENTIAL"):
            with self.subTest(value=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop("SECRET_KEY", None)
                else:
                    os.environ["SECRET_KEY"] = value
                with self.assertRaises(ImproperlyConfigured):
                    runpy.run_path(str(base))


class ProductionConfigurationTests(SimpleTestCase):
    def load_production(self, **environment):
        from video_creator.settings import base

        secret = environment.pop(
            "SECRET_KEY",
            "production-test-secret-with-more-than-fifty-unique-characters-123456",
        )
        with (
            patch.dict(
                os.environ,
                {
                    "ALLOWED_HOSTS": "video.example",
                    "FRONTEND_URL": "https://video.example",
                    **environment,
                },
            ),
            patch.object(base, "SECRET_KEY", secret),
        ):
            return runpy.run_path(
                str(settings.BASE_DIR / "video_creator/settings/production.py"),
                run_name="video_creator.settings.production",
            )

    def test_production_rejects_weak_keys_wildcard_hosts_and_http_origins(self):
        for environment in (
            {"SECRET_KEY": "short"},
            {"ALLOWED_HOSTS": "*"},
            {"FRONTEND_URL": "http://video.example"},
        ):
            with (
                self.subTest(environment=environment),
                self.assertRaises(ImproperlyConfigured),
            ):
                self.load_production(**environment)

    def test_https_redirect_proxy_detection_and_hsts(self):
        from django.http import HttpResponse
        from django.middleware.security import SecurityMiddleware
        from django.test import RequestFactory

        config = self.load_production()
        security = {
            name: config[name]
            for name in (
                "SECURE_SSL_REDIRECT",
                "SECURE_PROXY_SSL_HEADER",
                "SECURE_HSTS_SECONDS",
            )
        }
        with override_settings(ALLOWED_HOSTS=["video.example"], **security):
            middleware = SecurityMiddleware(lambda request: HttpResponse())
            factory = RequestFactory()
            redirect = middleware(factory.get("/api/csrf/", HTTP_HOST="video.example"))
            self.assertEqual(redirect.status_code, 301)
            self.assertEqual(redirect["Location"], "https://video.example/api/csrf/")
            response = middleware(
                factory.get(
                    "/api/csrf/",
                    HTTP_HOST="video.example",
                    HTTP_X_FORWARDED_PROTO="https",
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Strict-Transport-Security"], "max-age=31536000")
        self.assertEqual(
            config["CACHES"]["default"]["BACKEND"],
            "django.core.cache.backends.redis.RedisCache",
        )
        self.assertTrue(config["CSRF_COOKIE_HTTPONLY"])


class CSRFSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = user.make()
        self.owner.set_password("Strong-password-123")
        self.owner.save()
        self.client = APIClient(enforce_csrf_checks=True)
        self.access = str(RefreshToken.for_user(self.owner).access_token)

    def bootstrap(self):
        response = self.client.get(reverse("csrf-token"))
        self.assertEqual(response["Cache-Control"], "no-store")
        return response["X-CSRFToken"]

    def test_login_requires_csrf_and_rotates_token(self):
        data = {"username": self.owner.username, "password": "Strong-password-123"}
        self.assertEqual(self.client.post(reverse("login"), data).status_code, 403)
        token = self.bootstrap()
        cookie = self.client.cookies["csrftoken"].value
        response = self.client.post(reverse("login"), data, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(cookie, response.cookies["csrftoken"].value)
        self.assertTrue(response["X-CSRFToken"])

    def test_unsafe_cookie_requests_require_matching_csrf(self):
        self.client.cookies["access_token"] = self.access
        url = "/api/notifications/read_all/"
        self.assertEqual(self.client.patch(url).status_code, 403)
        token = self.bootstrap()
        self.assertEqual(
            self.client.patch(url, HTTP_X_CSRFTOKEN="x" * 32).status_code, 403
        )
        self.assertEqual(
            self.client.patch(url, HTTP_X_CSRFTOKEN=token).status_code, 200
        )
        self.assertEqual(
            self.client.patch(
                url, HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN="https://evil.example"
            ).status_code,
            403,
        )

    def test_bearer_only_requests_do_not_require_csrf(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        self.assertEqual(
            self.client.patch("/api/notifications/read_all/").status_code, 200
        )

    def test_refresh_and_logout_require_csrf_even_without_access_cookie(self):
        for endpoint in ("token_refresh", "logout"):
            with self.subTest(endpoint=endpoint):
                self.client.cookies["refresh_token"] = str(
                    RefreshToken.for_user(self.owner)
                )
                denied = self.client.post(reverse(endpoint))
                self.assertEqual(denied.status_code, 403)
                self.assertNotIn("access_token", denied.cookies)
                token = self.bootstrap()
                self.assertEqual(
                    self.client.post(
                        reverse(endpoint), HTTP_X_CSRFTOKEN=token
                    ).status_code,
                    200,
                )


class LoginRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    @override_settings(TRUSTED_PROXY_HOPS=0)
    @patch("apps.usermanagement.serializers.authenticate", return_value=None)
    def test_ip_limit_cannot_be_bypassed_with_forwarded_headers(self, authenticate):
        for index in range(10):
            response = self.client.post(
                reverse("login"),
                {"username": f"user{index}", "password": "bad"},
                HTTP_X_FORWARDED_FOR=f"192.0.2.{index}",
            )
            self.assertEqual(response.status_code, 401)
        response = self.client.post(
            reverse("login"), {"username": "another", "password": "bad"}
        )
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertEqual(authenticate.call_count, 10)

    def test_invalid_payload_is_a_client_error(self):
        response = self.client.post(reverse("login"), [], format="json")
        self.assertEqual(response.status_code, 400)

    @patch(
        "apps.usermanagement.throttling.cache.add",
        side_effect=ConnectionError("offline"),
    )
    @patch("apps.usermanagement.serializers.authenticate")
    def test_cache_failure_does_not_bypass_limits(self, authenticate, cache_add):
        response = self.client.post(
            reverse("login"), {"username": "target", "password": "bad"}
        )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("access_token", response.cookies)
        authenticate.assert_not_called()

    @patch("apps.usermanagement.serializers.authenticate", return_value=None)
    def test_account_limit_applies_across_source_ips(self, authenticate):
        for index in range(10):
            response = self.client.post(
                reverse("login"),
                {"username": "target", "password": "bad"},
                REMOTE_ADDR=f"192.0.2.{index}",
            )
            self.assertEqual(response.status_code, 401)
        response = self.client.post(
            reverse("login"),
            {"username": "target", "password": "bad"},
            REMOTE_ADDR="192.0.2.100",
        )
        self.assertEqual(response.status_code, 429)


class ProtectedMediaTests(TestCase):
    def setUp(self):
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        override = override_settings(MEDIA_ROOT=self.files.name)
        override.enable()
        self.addCleanup(override.disable)
        self.owner = user.make()
        self.other = user.make()
        self.project = video.make(
            created_by=self.owner, output="media/output/movie.mp4"
        )
        path = Path(self.files.name) / self.project.output.name
        path.parent.mkdir(parents=True)
        path.write_bytes(b"0123456789")
        self.url = "/media/output/movie.mp4"
        self.client = APIClient()

    def sign_in(self, owner):
        self.client.cookies["access_token"] = str(
            RefreshToken.for_user(owner).access_token
        )

    def test_anonymous_and_other_users_cannot_download_or_probe_ranges(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.sign_in(self.other)
        for method in (self.client.get, self.client.head):
            self.assertEqual(method(self.url, HTTP_RANGE="bytes=0-2").status_code, 404)

    def test_owner_can_seek_and_head(self):
        self.sign_in(self.owner)
        response = self.client.get(self.url, HTTP_RANGE="bytes=2-5")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], "bytes 2-5/10")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        response.close()
        self.assertEqual(self.client.head(self.url)["Content-Length"], "10")

    def test_unregistered_files_and_traversal_are_denied(self):
        self.sign_in(self.owner)
        for path in (
            "/media/output/unregistered.mp4",
            "/media/../.env",
            "/media/clips/source.mp4",
        ):
            self.assertEqual(self.client.get(path).status_code, 404)

    @override_settings(MEDIA_ACCEL_REDIRECT=True)
    def test_acceleration_is_only_issued_for_authorized_files(self):
        self.sign_in(self.other)
        self.assertNotIn("X-Accel-Redirect", self.client.get(self.url))
        self.sign_in(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(
            response["X-Accel-Redirect"], "/_protected_media/output/movie.mp4"
        )
        self.assertEqual(response["Content-Type"], "video/mp4")

    def test_archived_scene_files_still_belong_to_video_owner(self):
        from django.utils import timezone

        scene.make(
            video=self.project,
            voiceover="media/output/movie.mp4",
            archived_at=timezone.now(),
        )
        self.project.output = ""
        self.project.save(update_fields=["output"])
        self.sign_in(self.owner)
        self.assertEqual(self.client.head(self.url).status_code, 200)
        self.sign_in(self.other)
        self.assertEqual(self.client.head(self.url).status_code, 404)

    def test_shared_catalog_files_require_authentication(self):
        intro.make(created_by=None, file="media/output/movie.mp4")
        self.assertEqual(self.client.head(self.url).status_code, 401)
        self.sign_in(self.other)
        self.assertEqual(self.client.head(self.url).status_code, 200)
