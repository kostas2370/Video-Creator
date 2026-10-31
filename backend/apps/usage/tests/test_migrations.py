"""Exercise adoption and rollback with real records and permission grants."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class UsageAppMigrationTests(TransactionTestCase):
    old_targets = [
        ("videomanagement", "0051_scene_starting_asset_scene_starting_image_context"),
        ("usage", None),
    ]
    new_targets = [("usage", "0002_move_content_type")]

    def migrate(self, targets):
        MigrationExecutor(connection).migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_forward_and_backward_preserve_history_and_permissions(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(self.migrate, leaves)
        old = self.migrate(self.old_targets)
        owner = old.get_model("usermanagement", "User").objects.create(
            username="usage-migration-owner"
        )
        Usage = old.get_model("videomanagement", "AIUsage")
        record = Usage.objects.create(
            user_id=owner.pk, service="text", provider="OPENAI", model="test-model",
            key_source="personal", input_tokens=0, output_tokens=None,
            total_tokens=None, characters=17, images=2, seconds=3,
        )
        original = Usage.objects.values().get(pk=record.pk)
        ContentType = old.get_model("contenttypes", "ContentType")
        ct, _ = ContentType.objects.get_or_create(
            app_label="videomanagement", model="aiusage"
        )
        permission, _ = old.get_model("auth", "Permission").objects.get_or_create(
            content_type_id=ct.pk, codename="view_aiusage",
            defaults={"name": "Can view AI usage"},
        )
        group = old.get_model("auth", "Group").objects.create(name="Usage reviewers")
        owner.user_permissions.add(permission)
        group.permissions.add(permission)
        log = old.get_model("admin", "LogEntry").objects.create(
            user_id=owner.pk, content_type_id=ct.pk, object_id=str(record.pk),
            object_repr="Usage record", action_flag=2,
        )

        for targets, label in (
            (self.new_targets, "usage"),
            (self.old_targets, "videomanagement"),
            (self.new_targets, "usage"),
        ):
            with self.subTest(app=label):
                apps = self.migrate(targets)
                Usage = apps.get_model(label, "AIUsage")
                self.assertEqual(Usage._meta.db_table, "videomanagement_aiusage")
                self.assertEqual(Usage.objects.values().get(pk=record.pk), original)
                self.assertEqual(
                    apps.get_model("contenttypes", "ContentType").objects.get(pk=ct.pk).app_label,
                    label,
                )
                self.assertEqual(
                    apps.get_model("auth", "Permission").objects.get(pk=permission.pk).content_type_id,
                    ct.pk,
                )
                self.assertTrue(
                    apps.get_model("usermanagement", "User").objects.get(pk=owner.pk)
                    .user_permissions.filter(pk=permission.pk).exists()
                )
                self.assertTrue(
                    apps.get_model("auth", "Group").objects.get(pk=group.pk)
                    .permissions.filter(pk=permission.pk).exists()
                )
                self.assertEqual(
                    apps.get_model("admin", "LogEntry").objects.get(pk=log.pk).content_type_id,
                    ct.pk,
                )
