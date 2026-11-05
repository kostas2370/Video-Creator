from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from video_creator.urls import schema_view


class ApiSchemaTests(SimpleTestCase):
    def schema(self, user=None):
        request = APIRequestFactory().get("/swagger.json/", HTTP_HOST="localhost")
        if user is not None:
            force_authenticate(request, user=user)
        with self.assertNoLogs("drf_yasg", level="WARNING"):
            response = schema_view.without_ui(cache_timeout=0)(request, format=".json")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_public_schema_does_not_query_database_and_documents_library_filters(self):
        paths = self.schema()["paths"]
        path = next(path for path in paths if path.endswith("/media-assets/"))
        names = {parameter["name"] for parameter in paths[path]["get"]["parameters"]}
        self.assertTrue({"search", "kind"}.issubset(names))

    def test_authenticated_schema_does_not_run_request_dependent_queries(self):
        # Unsaved users and SimpleTestCase prohibit database access, even for
        # introspection of voices, scene serializers and owner-scoped resources.
        for is_superuser in (False, True):
            with self.subTest(is_superuser=is_superuser):
                schema = self.schema(get_user_model()(is_superuser=is_superuser))
                self.assertTrue(schema["paths"])
