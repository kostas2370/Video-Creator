from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from video_creator.urls import schema_view


class ApiSchemaTests(SimpleTestCase):
    def test_public_schema_uses_empty_querysets_and_documents_library_filters(self):
        request = APIRequestFactory().get("/swagger.json/", HTTP_HOST="localhost")
        with self.assertNoLogs("drf_yasg", level="WARNING"):
            response = schema_view.without_ui(cache_timeout=0)(request, format=".json")
        self.assertEqual(response.status_code, 200)
        paths = response.data["paths"]
        path = next(path for path in paths if path.endswith("/media-assets/"))
        names = {parameter["name"] for parameter in paths[path]["get"]["parameters"]}
        self.assertTrue({"search", "kind"}.issubset(names))
