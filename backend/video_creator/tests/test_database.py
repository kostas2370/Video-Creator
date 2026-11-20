import unittest
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from video_creator.settings.database import database_config


class DatabaseConfigurationTests(unittest.TestCase):
    def test_postgresql_is_default_with_request_scoped_connections(self):
        config = database_config(Path("/app"), environ={"POSTGRES_PASSWORD": "test"})
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["HOST"], "postgres")
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["CONN_MAX_AGE"], 0)

    def test_explicit_postgresql_configuration_is_used(self):
        config = database_config(
            Path("/app"),
            production=True,
            environ={
                "POSTGRES_DB": "viddie",
                "POSTGRES_USER": "app",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_HOST": "db.example.com",
                "POSTGRES_PORT": "6432",
                "POSTGRES_SSLMODE": "verify-full",
            },
        )
        self.assertEqual(config["NAME"], "viddie")
        self.assertEqual(config["USER"], "app")
        self.assertEqual(config["HOST"], "db.example.com")
        self.assertEqual(config["PORT"], "6432")
        self.assertEqual(config["OPTIONS"]["sslmode"], "verify-full")

    def test_postgresql_requires_a_password(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config(Path("/app"), environ={})

    def test_sqlite_is_only_an_explicit_local_fallback(self):
        config = database_config(Path("/app"), environ={"DATABASE_ENGINE": "sqlite"})
        self.assertEqual(config["NAME"], Path("/app/db.sqlite3"))
        with self.assertRaises(ImproperlyConfigured):
            database_config(
                Path("/app"), production=True, environ={"DATABASE_ENGINE": "sqlite"}
            )

    def test_unknown_engine_fails_instead_of_using_another_database(self):
        with self.assertRaises(ImproperlyConfigured):
            database_config(Path("/app"), environ={"DATABASE_ENGINE": "wrong"})
