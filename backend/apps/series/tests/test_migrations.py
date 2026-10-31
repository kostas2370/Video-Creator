"""Verify the app move against populated tables and existing permission grants."""

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class SeriesAppMigrationTests(TransactionTestCase):
    old_targets = [("videomanagement", "0048_episode_memory_source"), ("series", None)]
    new_targets = [("series", "0002_move_content_types")]

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def setUp(self):
        self.addCleanup(
            self.migrate, MigrationExecutor(connection).loader.graph.leaf_nodes()
        )
        self.old_apps = self.migrate(self.old_targets)

    def test_forward_and_backward_preserve_records_relations_and_permissions(self):
        old = self.old_apps
        User = old.get_model("usermanagement", "User")
        owner = User.objects.create(username="series-migration-owner")
        Video = old.get_model("videomanagement", "Video")
        prompt = old.get_model("videomanagement", "UserPrompt").objects.create()
        video = Video.objects.create(created_by=owner, title="Episode", prompt=prompt)
        Series = old.get_model("videomanagement", "VideoSeries")
        series = Series.objects.create(
            created_by=owner,
            title="Milo",
            premise="Science",
            visual_style="Watercolor",
            reference_image="media/series/existing.png",
        )
        Episode = old.get_model("videomanagement", "SeriesEpisode")
        episode = Episode.objects.create(
            series=series,
            video=video,
            number=3,
            idea="Shadows",
            summary="Found a lamp",
            memory_source_hash="a" * 64,
            is_canon=True,
            profile_snapshot={"title": "Milo"},
            generation_params={"series_context": "saved"},
        )
        ContentType = old.get_model("contenttypes", "ContentType")
        Permission = old.get_model("auth", "Permission")
        Group = old.get_model("auth", "Group")
        group = Group.objects.create(name="Series editors")
        content_type_ids = {}
        permission_ids = {}
        for model in ("videoseries", "seriesepisode"):
            ct, _ = ContentType.objects.get_or_create(
                app_label="videomanagement", model=model
            )
            permission, _ = Permission.objects.get_or_create(
                content_type=ct,
                codename=f"change_{model}",
                defaults={"name": f"Can change {model}"},
            )
            owner.user_permissions.add(permission)
            group.permissions.add(permission)
            content_type_ids[model] = ct.pk
            permission_ids[model] = permission.pk

        for targets, label in (
            (self.new_targets, "series"),
            (self.old_targets, "videomanagement"),
        ):
            with self.subTest(app=label):
                apps = self.migrate(targets)
                moved = (
                    apps.get_model(label, "SeriesEpisode")
                    .objects.select_related("series", "video")
                    .get(pk=episode.pk)
                )
                self.assertEqual(moved.series_id, series.pk)
                self.assertEqual(moved.video_id, video.pk)
                self.assertEqual(moved.series.created_by_id, owner.pk)
                self.assertEqual(
                    moved.series.reference_image.name, "media/series/existing.png"
                )
                self.assertEqual(moved.number, 3)
                self.assertEqual(moved.summary, "Found a lamp")
                self.assertEqual(moved.memory_source_hash, "a" * 64)
                self.assertTrue(moved.is_canon)
                self.assertEqual(moved.profile_snapshot, {"title": "Milo"})
                self.assertEqual(moved.generation_params, {"series_context": "saved"})
                for model, ct_id in content_type_ids.items():
                    ct = apps.get_model("contenttypes", "ContentType").objects.get(
                        pk=ct_id
                    )
                    self.assertEqual(ct.app_label, label)
                    self.assertEqual(ct.model, model)
                    permission = apps.get_model("auth", "Permission").objects.get(
                        pk=permission_ids[model]
                    )
                    self.assertEqual(permission.content_type_id, ct_id)
                    self.assertTrue(
                        apps.get_model("usermanagement", "User")
                        .objects.get(pk=owner.pk)
                        .user_permissions.filter(pk=permission.pk)
                        .exists()
                    )
                    self.assertTrue(
                        apps.get_model("auth", "Group")
                        .objects.get(pk=group.pk)
                        .permissions.filter(pk=permission.pk)
                        .exists()
                    )


class StructuredCharacterMigrationTests(TransactionTestCase):
    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        loader = MigrationExecutor(connection).loader
        return loader.project_state(list(loader.applied_migrations)).apps

    def test_keeps_three_approved_characters_and_their_reference_files(self):
        self.addCleanup(self.migrate, MigrationExecutor(connection).loader.graph.leaf_nodes())
        old = self.migrate([("series", "0004_characterreference")])
        owner = old.get_model("usermanagement", "User").objects.create(username="approved-cast-owner")
        Reference = old.get_model("series", "CharacterReference")
        cast = []
        files = {}
        from uuid import uuid4
        for name in ("Bananito", "Bananita", "Bruno"):
            brief = {"name": name, "appearance": "Yellow banana", "wardrobe": "", "visual_style": "3D"}
            reference = Reference.objects.create(
                created_by_id=owner.pk, status="READY", description=brief,
                image=f"media/characters/{uuid4().hex}.png",
            )
            files[reference.pk] = reference.image.name
            character = {"id": str(uuid4()), "name": name, "appearance": "Yellow banana", "wardrobe": "", "personality": "Curious", "relationships": "Friends", "reference_id": str(reference.pk)}
            character["reference_approval"] = {"reference_id": str(reference.pk), **brief}
            cast.append(character)
        series = old.get_model("series", "VideoSeries").objects.create(
            created_by_id=owner.pk, title="Fruit story", premise="Relationships",
            visual_style="3D", narration=False, cast=cast,
        )
        new = self.migrate([("series", "0005_structured_characters")])
        profiles = list(new.get_model("series", "SeriesCharacter").objects.filter(series_id=series.pk).order_by("position"))
        self.assertEqual(len(profiles), 3)
        for original, profile in zip(cast, profiles):
            self.assertEqual(str(profile.character_id), original["id"])
            self.assertEqual(str(profile.reference_id), original["reference_id"])
            self.assertEqual(profile.reference_approval, original["reference_approval"])
            reference = new.get_model("series", "CharacterReference").objects.get(pk=profile.reference_id)
            self.assertEqual(reference.name, original["name"])
            self.assertEqual(reference.image.name, files[reference.pk])
            self.assertEqual(reference.status, "READY")
