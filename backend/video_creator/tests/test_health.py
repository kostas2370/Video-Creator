from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase
from redis.exceptions import ConnectionError


class HealthTests(SimpleTestCase):
    def test_liveness_does_not_require_dependencies_or_login(self):
        response = self.client.get("/api/health/live/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("no-store", response["Cache-Control"])

    @patch("video_creator.health.Redis.from_url")
    @patch("video_creator.health.connection")
    def test_readiness_checks_database_and_broker(self, database, redis):
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 200)
        database.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1"
        )
        redis.return_value.__enter__.return_value.ping.assert_called_once()

    @patch("video_creator.health.Redis.from_url")
    @patch("video_creator.health.connection")
    def test_database_failure_returns_503_without_connection_details(
        self, database, redis
    ):
        database.cursor.side_effect = OperationalError("private connection details")
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        redis.assert_not_called()

    @patch("video_creator.health.Redis.from_url")
    @patch("video_creator.health.connection")
    def test_broker_failure_returns_503_without_connection_details(
        self, database, redis
    ):
        redis.return_value.__enter__.return_value.ping.side_effect = ConnectionError(
            "private connection details"
        )
        response = self.client.get("/api/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
