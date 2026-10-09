import json

from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user

from ..models import ApiKeys, AuthType, UserCustomVisualProvider, VisualOutputType


class CustomVisualProviderApiTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.stranger = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.provider = UserCustomVisualProvider.objects.create(
            user=self.user,
            name="Studio images",
            output_type=VisualOutputType.IMAGE,
            endpoint_url="https://example.com/images",
            api_key="saved-secret-credential",
        )
        self.list_url = reverse("user-custom-visual-providers-list")
        self.detail_url = reverse(
            "user-custom-visual-providers-detail", args=[str(self.provider.pk)]
        )

    def payload(self, **overrides):
        data = {
            "name": "Studio videos",
            "output_type": "VIDEO",
            "endpoint_url": "https://example.com/videos",
            "auth_type": "header",
            "auth_header_name": "x-api-key",
            "api_key": "new-secret-credential",
            "prompt_field_name": "input",
        }
        data.update(overrides)
        return data

    def test_creates_image_and_video_configs_for_the_caller(self):
        for output_type in VisualOutputType.values:
            with self.subTest(output_type=output_type):
                response = self.client.post(
                    self.list_url,
                    self.payload(
                        name=f"Studio {output_type}",
                        output_type=output_type,
                        user=self.stranger.pk,
                    ),
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.data)
                provider = UserCustomVisualProvider.objects.get(pk=response.data["id"])
                self.assertEqual(provider.user, self.user)
                self.assertEqual(provider.output_type, output_type)
                self.assertEqual(provider.prompt_field_name, "input")
                self.assertEqual(provider.api_key, "new-secret-credential")
                self.assertNotIn(provider.api_key, json.dumps(response.data))
                self.assertIn("created_at", response.data)

    def test_lists_only_owned_configs_with_masked_credentials(self):
        UserCustomVisualProvider.objects.create(
            user=self.stranger,
            name="Private",
            output_type="VIDEO",
            endpoint_url="https://example.com/private",
        )
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [str(self.provider.pk)])
        self.assertEqual(
            response.data[0]["api_key"], ApiKeys.mask(self.provider.api_key)
        )
        self.assertNotIn(self.provider.api_key, json.dumps(response.data))

    def test_detail_masks_the_credential(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["api_key"], ApiKeys.mask(self.provider.api_key))
        self.assertNotIn(self.provider.api_key, json.dumps(response.data))

    def test_connection_updates_preserve_omitted_credentials(self):
        response = self.client.patch(
            self.detail_url,
            {
                "endpoint_url": "https://example.com/new",
                "prompt_field_name": "description",
                "user": self.stranger.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.api_key, "saved-secret-credential")
        self.assertEqual(self.provider.user, self.user)
        self.assertEqual(self.provider.prompt_field_name, "description")

    def test_credentials_can_be_replaced_or_explicitly_cleared(self):
        for credential in ("replacement-secret", ""):
            with self.subTest(credential=credential):
                response = self.client.patch(
                    self.detail_url, {"api_key": credential}, format="json"
                )
                self.assertEqual(response.status_code, 200)
                self.provider.refresh_from_db()
                self.assertEqual(self.provider.api_key, credential)
                self.assertEqual(response.data["api_key"], ApiKeys.mask(credential))

    def test_names_are_unique_per_user(self):
        payload = self.payload(name=self.provider.name)
        self.assertEqual(
            self.client.post(self.list_url, payload, format="json").status_code, 400
        )
        self.client.force_authenticate(self.stranger)
        self.assertEqual(
            self.client.post(self.list_url, payload, format="json").status_code, 201
        )

    def test_names_cannot_be_renamed(self):
        response = self.client.patch(
            self.detail_url, {"name": "Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.name, "Studio images")

    def test_rejects_builtin_provider_names(self):
        for name in (
            "OPENAI",
            "sora",
            "Stable-Diffusion",
            "midjourney",
            "bing",
            "google",
        ):
            with self.subTest(name=name):
                response = self.client.post(
                    self.list_url, self.payload(name=name), format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("name", response.data)

    def test_rejects_invalid_configurations(self):
        for data, field in (
            ({"endpoint_url": "invalid"}, "endpoint_url"),
            ({"output_type": "AUDIO"}, "output_type"),
            ({"auth_type": "invalid"}, "auth_type"),
            ({"prompt_field_name": ""}, "prompt_field_name"),
            ({"auth_type": "header", "auth_header_name": ""}, "auth_header_name"),
        ):
            with self.subTest(field=field):
                response = self.client.patch(self.detail_url, data, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_partial_updates_reuse_the_saved_header_name(self):
        self.provider.auth_type = AuthType.HEADER
        self.provider.auth_header_name = "x-api-key"
        self.provider.save()
        response = self.client.patch(
            self.detail_url, {"api_key": "replacement"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_put_replaces_connection_without_reassigning_ownership(self):
        response = self.client.put(
            self.detail_url,
            self.payload(name=self.provider.name, user=self.stranger.pk),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.user, self.user)
        self.assertEqual(self.provider.output_type, "VIDEO")

    def test_other_users_cannot_read_update_or_delete_the_config(self):
        self.client.force_authenticate(self.stranger)
        for method, data in (
            ("get", None),
            ("patch", {"api_key": "stolen"}),
            ("put", self.payload()),
            ("delete", None),
        ):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.detail_url, data, format="json"
                )
                self.assertEqual(response.status_code, 404)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.api_key, "saved-secret-credential")

    def test_all_crud_actions_require_authentication(self):
        self.client.force_authenticate(None)
        for method, url, data in (
            ("get", self.list_url, None),
            ("post", self.list_url, self.payload()),
            ("get", self.detail_url, None),
            ("patch", self.detail_url, {}),
            ("put", self.detail_url, self.payload()),
            ("delete", self.detail_url, None),
        ):
            with self.subTest(method=method):
                self.assertEqual(
                    getattr(self.client, method)(url, data, format="json").status_code,
                    401,
                )

    def test_delete_removes_the_config(self):
        self.assertEqual(self.client.delete(self.detail_url).status_code, 204)
        self.assertFalse(
            UserCustomVisualProvider.objects.filter(pk=self.provider.pk).exists()
        )

    def test_minimal_config_uses_authentication_and_prompt_defaults(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Minimal",
                "output_type": "IMAGE",
                "endpoint_url": "https://example.com/generate",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["auth_type"], "bearer")
        self.assertEqual(response.data["prompt_field_name"], "prompt")
        self.assertEqual(response.data["api_key"], "")

    def test_output_type_is_required(self):
        payload = self.payload()
        payload.pop("output_type")
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("output_type", response.data)

    def test_credentials_are_encrypted_at_rest(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT api_key FROM apikeysmanagement_usercustomvisualprovider WHERE id = %s",
                [self.provider._meta.pk.get_db_prep_value(self.provider.pk, connection)],
            )
            encrypted = cursor.fetchone()[0]
        self.assertNotIn(self.provider.api_key, encrypted)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.api_key, "saved-secret-credential")

    def test_model_builds_headers_for_each_authentication_mode(self):
        for auth_type in AuthType.values:
            with self.subTest(auth_type=auth_type):
                self.provider.auth_type = auth_type
                self.provider.auth_header_name = "x-api-key"
                self.provider.api_key = "username:password"
                headers, auth = self.provider.get_auth_headers()
                self.assertEqual(headers["Content-Type"], "application/json")
                if auth_type == AuthType.BEARER:
                    self.assertEqual(
                        headers["Authorization"], "Bearer username:password"
                    )
                elif auth_type == AuthType.HEADER:
                    self.assertEqual(headers["x-api-key"], "username:password")
                elif auth_type == AuthType.BASIC:
                    self.assertEqual(
                        (auth.username, auth.password), ("username", "password")
                    )
                else:
                    self.assertNotIn("Authorization", headers)
                    self.assertNotIn("x-api-key", headers)
                if auth_type != AuthType.BASIC:
                    self.assertIsNone(auth)
