from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.usermanagement.baker_recipes import user
from ..models import UserCustomTTSProvider, UserCustomVisualProvider


class ExtraParametersApiTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.configs = (
            (UserCustomTTSProvider, "user-custom-tts-providers", {}),
            (
                UserCustomVisualProvider,
                "user-custom-visual-providers",
                {"output_type": "IMAGE"},
            ),
        )

    def test_create_read_update_preserve_and_clear_parameters_for_both_types(self):
        parameters = {
            "model": "my-model",
            "speed": 1.1,
            "options": {"seed": 3},
            "enabled": False,
        }
        for model, route, fields in self.configs:
            with self.subTest(model=model):
                response = self.client.post(
                    reverse(route + "-list"),
                    {
                        "name": "Studio",
                        "endpoint_url": "https://example.com/generate",
                        "auth_type": "none",
                        "extra_parameters": parameters,
                        **fields,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.data)
                provider = model.objects.get(pk=response.data["id"])
                self.assertEqual(provider.extra_parameters, parameters)
                detail = reverse(route + "-detail", args=[provider.pk])
                self.assertEqual(
                    self.client.get(detail).data["extra_parameters"], parameters
                )
                response = self.client.patch(
                    detail, {"endpoint_url": "https://example.com/new"}, format="json"
                )
                self.assertEqual(response.data["extra_parameters"], parameters)
                response = self.client.patch(
                    detail, {"extra_parameters": {"seed": 7}}, format="json"
                )
                self.assertEqual(response.data["extra_parameters"], {"seed": 7})
                response = self.client.patch(
                    detail, {"extra_parameters": {}}, format="json"
                )
                self.assertEqual(response.data["extra_parameters"], {})
                provider.refresh_from_db()
                self.assertEqual(provider.extra_parameters, {})

    def test_defaults_are_empty_objects(self):
        for model, route, fields in self.configs:
            with self.subTest(model=model):
                response = self.client.post(
                    reverse(route + "-list"),
                    {
                        "name": "Studio",
                        "endpoint_url": "https://example.com/generate",
                        "auth_type": "none",
                        **fields,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(response.data["extra_parameters"], {})

    def test_rejects_non_objects_on_create_and_update(self):
        for model, route, fields in self.configs:
            provider = model.objects.create(
                user=self.user,
                name="Studio",
                endpoint_url="https://example.com/generate",
                **fields,
            )
            for invalid in (None, [], ["a"], "string", 42, True):
                with self.subTest(model=model, invalid=invalid):
                    response = self.client.post(
                        reverse(route + "-list"),
                        {
                            "name": "New Studio",
                            "endpoint_url": "https://example.com/generate",
                            "extra_parameters": invalid,
                            **fields,
                        },
                        format="json",
                    )
                    self.assertEqual(response.status_code, 400, response.data)
                    self.assertIn("extra_parameters", response.data)
                    response = self.client.patch(
                        reverse(route + "-detail", args=[provider.pk]),
                        {
                            "extra_parameters": invalid,
                        },
                        format="json",
                    )
                    self.assertEqual(response.status_code, 400, response.data)
                    provider.refresh_from_db()
                    self.assertEqual(provider.extra_parameters, {})
