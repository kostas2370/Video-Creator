from django.test import SimpleTestCase
from django.urls import resolve


class AuthenticationRouteTests(SimpleTestCase):
    def test_only_the_apps_verified_login_flow_is_exposed(self):
        self.assertEqual(resolve("/api/login/").url_name, "login")
        self.assertEqual(resolve("/api/register/").url_name, "register")
        self.assertEqual(resolve("/api/token/refresh/").url_name, "token_refresh")
        for path in ("/api/auth/jwt/create/", "/api/auth/users/"):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.post(path, {"username": "probe"}).status_code, 404
                )
