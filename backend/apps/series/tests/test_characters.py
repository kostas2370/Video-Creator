import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.series.models import Character, SeriesEpisode, VideoSeries
from apps.series.serializers import VideoSeriesSerializer, serialize_cast
from apps.series.services.characters import (
    generate_reference,
    replace_series_cast,
    save_reference_image,
)
from apps.usermanagement.baker_recipes import user
from apps.videomanagement.models import MediaAsset
from apps.videomanagement.services.videos.generation import generate_video
from apps.videomanagement.tests.api.base import ApiTestCase


class CharacterSetupTests(ApiTestCase):
    def test_character_description_is_a_reviewable_draft_and_preserves_the_supplied_name(
        self,
    ):
        series = self.profile(cast=[self.character()])
        original = serialize_cast(series)
        with (
            patch(
                "apps.series.services.characters.get_update_sentence",
                return_value=json.dumps(
                    {
                        "cast": [
                            {
                                "name": "Another name",
                                "appearance": "Orange fox with cream muzzle",
                                "personality": "Shy detective",
                            }
                        ]
                    }
                ),
            ) as ai,
            patch(
                "apps.series.tasks.generate_character_reference_task.delay"
            ) as images,
        ):
            response = self.client.post(
                reverse("series-character-description"),
                {
                    "premise": "Fox mysteries",
                    "visual_style": "Watercolor",
                    "story_format": "ANIMATED_STORY",
                    "name": "Milo",
                    "idea": "A shy detective",
                    "appearance": "Orange fox",
                    "cast_names": ["Milo", "Rin"],
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["character"]["name"], "Milo")
        self.assertEqual(response.data["character"]["personality"], "Shy detective")
        self.assertNotIn("id", response.data["character"])
        self.assertIn("A shy detective", ai.call_args.args[0])
        series.refresh_from_db()
        self.assertEqual(serialize_cast(series), original)
        images.assert_not_called()

    def test_character_description_rejects_invalid_input_before_calling_ai(self):
        with patch("apps.series.services.characters.get_update_sentence") as ai:
            response = self.client.post(
                reverse("series-character-description"),
                {
                    "premise": "Mystery",
                    "visual_style": "3D",
                    "story_format": "GENERAL",
                    "count": 2,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        ai.assert_not_called()

    def setUp(self):
        super().setUp()
        self.files = tempfile.TemporaryDirectory()
        self.addCleanup(self.files.cleanup)
        storage = override_settings(MEDIA_ROOT=self.files.name)
        storage.enable()
        self.addCleanup(storage.disable)
        self.choices = {
            "name": "Milo",
            "appearance": "Orange fox, cream muzzle",
            "wardrobe": "Teal scarf",
            "visual_style": "Watercolor",
        }

    def upload(self, color="orange"):
        image = io.BytesIO()
        Image.new("RGB", (64, 64), color).save(image, format="PNG")
        return self.client.post(
            reverse("series-character-references"),
            {
                **self.choices,
                "image": SimpleUploadedFile(
                    "reference.png", image.getvalue(), content_type="image/png"
                ),
            },
            format="multipart",
        )

    def profile(self, **changes):
        cast = changes.pop("cast", [])
        series = VideoSeries.objects.create(
            created_by=self.user,
            title="Milo",
            premise="A fox and his rival",
            visual_style="Watercolor",
            narration=False,
            **changes,
        )
        replace_series_cast(series, cast)
        return series

    def character(self, reference=None):
        character = {
            "id": str(uuid4()),
            "name": "Milo",
            "appearance": self.choices["appearance"],
            "wardrobe": "Teal scarf",
            "personality": "Curious",
            "relationships": "",
        }
        if reference:
            character.update(
                id=reference["id"],
                image=reference.get("pending_image") or reference["image"],
                image_approved=True,
                visual_style="Watercolor",
            )
        return character

    def test_ai_cast_is_an_unsaved_draft_with_no_image_requests(self):
        cast = [
            {"name": "Milo", "appearance": "Orange fox"},
            {"name": "Rin", "appearance": "White rabbit"},
        ]
        with (
            patch(
                "apps.series.services.characters.get_update_sentence",
                return_value=json.dumps({"cast": cast}),
            ) as ai,
            patch(
                "apps.series.tasks.generate_character_reference_task.delay"
            ) as images,
        ):
            response = self.client.post(
                reverse("series-cast-draft"),
                {
                    "premise": "Rivals become friends",
                    "visual_style": "3D animation",
                    "story_format": "ANIMATED_STORY",
                    "count": 2,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["name"] for row in response.data["cast"]], ["Milo", "Rin"]
        )
        self.assertNotEqual(
            response.data["cast"][0]["id"], response.data["cast"][1]["id"]
        )
        self.assertIn("Rivals become friends", ai.call_args.args[0])
        self.assertFalse(VideoSeries.objects.exists())
        self.assertFalse(Character.objects.exists())
        images.assert_not_called()

    def test_invalid_ai_cast_does_not_replace_any_saved_profiles(self):
        series = self.profile(cast=[self.character()])
        with patch(
            "apps.series.services.characters.get_update_sentence",
            return_value='{"cast": []}',
        ):
            response = self.client.post(
                reverse("series-cast-draft"),
                {
                    "premise": "Rivals",
                    "visual_style": "3D",
                    "story_format": "SERIAL_DRAMA",
                    "count": 2,
                },
                format="json",
            )
        self.assertEqual(response.status_code, 500)
        series.refresh_from_db()
        self.assertEqual(serialize_cast(series)[0]["name"], "Milo")

    def test_uploaded_references_are_normalized_and_owner_scoped(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        reference = Character.objects.get(pk=response.data["id"])
        self.assertEqual(reference.status, "READY")
        with Image.open(reference.image.path) as image:
            self.assertEqual(image.format, "PNG")
        self.assertEqual(
            self.client.get(
                reverse("series-character-references"), {"id": reference.pk}
            ).status_code,
            200,
        )
        reference.created_by = user.make()
        reference.save()
        self.assertEqual(
            self.client.get(
                reverse("series-character-references"), {"id": reference.pk}
            ).status_code,
            404,
        )
        series = self.profile()
        response = self.client.patch(
            reverse("series-detail", args=[series.pk]),
            {
                "cast": [
                    self.character(
                        {"id": str(reference.pk), "image": reference.image.url}
                    )
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_generation_is_queued_and_a_job_cannot_generate_twice(self):
        with patch(
            "apps.series.tasks.generate_character_reference_task.delay"
        ) as queue:
            response = self.client.post(
                reverse("series-character-references"), self.choices, format="json"
            )
        self.assertEqual(response.status_code, 202, response.data)
        identifier = response.data["id"]
        queue.assert_called_once_with(
            identifier, str(Character.objects.get(pk=identifier).job_id), self.choices
        )
        path = Path(self.files.name) / "generated.png"
        Image.new("RGB", (32, 32), "orange").save(path)
        with patch(
            "apps.series.services.characters.openai_images.generate_openai_image",
            return_value=str(path),
        ) as generate:
            generate_reference(
                identifier, Character.objects.get(pk=identifier).job_id, self.choices
            )
            generate_reference(
                identifier, Character.objects.get(pk=identifier).job_id, self.choices
            )
        generate.assert_called_once()
        self.assertIn("single-character identity reference", generate.call_args.args[0])
        reference = Character.objects.get(pk=identifier)
        self.assertEqual(reference.status, "READY")
        self.assertTrue(reference.image.storage.exists(reference.image.name))

    def test_generation_failures_are_safe_and_leave_previous_images_intact(self):
        previous = self.upload().data
        reference = Character.objects.create(
            created_by=self.user, status="QUEUED", **self.choices
        )
        with patch(
            "apps.series.services.characters.openai_images.generate_openai_image",
            side_effect=RuntimeError("private provider details"),
        ):
            generate_reference(reference.pk, reference.job_id, self.choices)
        response = self.client.get(
            reverse("series-character-references"), {"id": reference.pk}
        )
        self.assertEqual(response.data["status"], "FAILED")
        self.assertNotIn("private provider details", response.data["error"])
        self.assertEqual(Character.objects.get(pk=previous["id"]).status, "READY")

    def test_pending_image_requests_can_be_saved_but_must_belong_to_the_owner(self):
        reference = Character.objects.create(
            created_by=self.user, status="QUEUED", **self.choices
        )
        series = self.profile(story_format="SERIAL_DRAMA")
        character = self.character() | {"id": str(reference.pk)}
        response = self.client.patch(
            reverse("series-detail", args=[series.pk]),
            {"cast": [character]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["cast"][0]["status"], "QUEUED")
        self.assertFalse(response.data["cast_ready"])
        reference.created_by = user.make()
        reference.save()
        response = self.client.patch(
            reverse("series-detail", args=[series.pk]),
            {"cast": [character]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_queue_failure_is_reported_and_does_not_touch_existing_references(self):
        with patch(
            "apps.series.tasks.generate_character_reference_task.delay",
            side_effect=RuntimeError("broker unavailable"),
        ):
            response = self.client.post(
                reverse("series-character-references"), self.choices, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(Character.objects.get().status, "FAILED")

    def test_episode_requires_approved_images_and_changes_require_review(self):
        reference = self.upload().data
        character = self.character(reference)
        for changes in (
            {"cast": []},
            {"cast": [self.character()]},
            {
                "cast": [
                    {**character, "appearance": "Blue fox", "image_approved": False}
                ]
            },
            {"cast": [character], "visual_style": "Photorealistic"},
        ):
            series = self.profile(story_format="ANIMATED_STORY")
            for field, value in changes.items():
                if field == "cast":

                    replace_series_cast(series, value)
                else:
                    setattr(series, field, value)
            series.save()
            with patch("apps.videomanagement.tasks.generate_video_task.delay") as queue:
                response = self.client.post(
                    reverse("series-episodes", args=[series.pk]),
                    {"idea": "Find a lantern"},
                    format="json",
                )
            self.assertEqual(response.status_code, 400, response.data)
            queue.assert_not_called()
            replace_series_cast(series, [])
        self.assertFalse(SeriesEpisode.objects.exists())

    def test_episode_copies_a_cast_sheet_and_later_cast_edits_cannot_change_it(self):
        reference = self.upload().data
        series = self.profile(
            story_format="SERIAL_DRAMA", cast=[self.character(reference)]
        )
        with patch("apps.videomanagement.tasks.generate_video_task.delay"):
            response = self.client.post(
                reverse("series-episodes", args=[series.pk]),
                {"idea": "Find a lantern"},
                format="json",
            )
        self.assertEqual(response.status_code, 202, response.data)
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        self.assertTrue(episode.video.settings["character_references"])
        with episode.video.reference_image.open("rb") as source:
            saved = source.read()

        replace_series_cast(series, [self.character(self.upload("blue").data)])
        series.save()
        with episode.video.reference_image.open("rb") as source:
            self.assertEqual(source.read(), saved)
        with Image.open(io.BytesIO(saved)) as sheet:
            self.assertEqual(sheet.size, (512, 568))
        self.assertEqual(episode.profile_snapshot["cast"][0]["id"], reference["id"])

    def test_storyboard_preparation_retains_the_character_reference_workflow(self):
        series = self.profile(
            story_format="ANIMATED_STORY", cast=[self.character(self.upload().data)]
        )
        with patch("apps.videomanagement.tasks.generate_video_task.delay"):
            response = self.client.post(
                reverse("series-episodes", args=[series.pk]),
                {"idea": "Milo finds a lantern"},
                format="json",
            )
        episode = SeriesEpisode.objects.get(pk=response.data["id"])
        with (
            patch(
                "apps.videomanagement.services.videos.generation.get_reply",
                return_value={
                    "title": "Lantern",
                    "visual_continuity": "Orange fox",
                    "episode_summary": "Milo found a lantern.",
                    "scenes": [],
                },
            ),
            patch(
                "apps.videomanagement.services.videos.generation.generate_directory",
                return_value=self.files.name,
            ),
            patch(
                "apps.videomanagement.services.videos.generation.VoiceModel.select_voice",
                return_value=None,
            ),
        ):
            generate_video(episode.video, **episode.generation_params)
        episode.video.refresh_from_db()
        self.assertTrue(episode.video.settings["character_references"])
        self.assertEqual(episode.video.status, "REVIEW")

    def test_new_look_stays_pending_on_the_same_character_until_accepted(self):
        reference = self.upload().data
        series = self.profile(cast=[self.character(reference)])
        character = Character.objects.get(pk=reference["id"])
        original = character.image.name
        image = io.BytesIO()
        Image.new("RGB", (64, 64), "blue").save(image, format="PNG")
        response = self.client.post(
            reverse("series-character-references"),
            {
                **self.choices,
                "id": str(character.pk),
                "image": SimpleUploadedFile(
                    "new.png", image.getvalue(), content_type="image/png"
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["id"], str(character.pk))
        character.refresh_from_db()
        self.assertEqual(character.image.name, original)
        self.assertTrue(character.image.storage.exists(original))
        self.assertTrue(character.image_approved)
        self.assertTrue(character.pending_image)
        new_image = character.pending_image.name
        selected = self.character(reference) | {"image": response.data["pending_image"]}
        saved = self.client.patch(
            reverse("series-detail", args=[series.pk]),
            {"cast": [selected]},
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.data)
        character.refresh_from_db()
        self.assertEqual(character.image.name, new_image)
        self.assertFalse(character.pending_image)
        self.assertTrue(character.image.storage.exists(new_image))
        self.assertTrue(character.image_approved)
        self.assertEqual(Character.objects.count(), 1)

    def test_cannot_replace_another_accounts_character_by_id(self):
        other = Character.objects.create(
            created_by=user.make(), name="Other", appearance="Fox"
        )
        with patch(
            "apps.series.tasks.generate_character_reference_task.delay"
        ) as queue:
            response = self.client.post(
                reverse("series-character-references"),
                {**self.choices, "id": str(other.pk)},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        queue.assert_not_called()
        other.refresh_from_db()
        self.assertEqual(other.name, "Other")

    def test_series_save_validated_before_completion_keeps_the_new_pending_image(self):
        reference = self.upload().data
        series = self.profile(cast=[self.character(reference)])
        character = Character.objects.get(pk=reference["id"])
        character.status = Character.Status.GENERATING
        character.job_id = uuid4()
        character.save()
        request = Request(APIRequestFactory().patch("/"))
        request._user = self.user
        serializer = VideoSeriesSerializer(
            series,
            data={"cast": serialize_cast(series)},
            partial=True,
            context={"request": request},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        original = character.image.name
        image = io.BytesIO()
        Image.new("RGB", (32, 32), "blue").save(image, format="PNG")
        image.seek(0)
        completed = save_reference_image(
            character, image, character.job_id, character.generation_brief()
        )
        pending = completed.pending_image.name
        serializer.save()
        character.refresh_from_db()
        self.assertEqual(character.image.name, original)
        self.assertEqual(character.pending_image.name, pending)
        self.assertEqual(character.status, Character.Status.READY)
        self.assertTrue(character.image_approved)

    def test_superseded_job_archives_its_image_without_overwriting_the_new_request(
        self,
    ):
        reference = Character.objects.create(
            created_by=self.user, job_id=uuid4(), status="GENERATING", **self.choices
        )
        old_job = reference.job_id
        new_job = uuid4()
        Character.objects.filter(pk=reference.pk).update(
            job_id=new_job, status="QUEUED"
        )
        image = io.BytesIO()
        Image.new("RGB", (32, 32), "blue").save(image, format="PNG")
        image.seek(0)
        save_reference_image(reference, image, old_job, reference.generation_brief())
        reference.refresh_from_db()
        self.assertEqual(reference.job_id, new_job)
        self.assertEqual(reference.status, "QUEUED")
        self.assertFalse(reference.image)
        self.assertFalse(reference.pending_image)
        asset = MediaAsset.objects.get(created_by=self.user)
        self.assertTrue(asset.file.storage.exists(asset.file.name))

    def test_edit_during_generation_cannot_attach_an_image_for_the_old_description(
        self,
    ):
        character = Character.objects.create(
            created_by=self.user, job_id=uuid4(), status="QUEUED", **self.choices
        )
        series = self.profile(cast=[self.character() | {"id": str(character.pk)}])
        path = Path(self.files.name) / "old-description.png"
        Image.new("RGB", (32, 32), "orange").save(path)

        def finish_old_image(*args, **kwargs):
            replace_series_cast(
                series,
                [
                    {
                        **self.character(),
                        "id": str(character.pk),
                        "appearance": "Blue fox",
                    }
                ],
            )
            return str(path)

        with patch(
            "apps.series.services.characters.openai_images.generate_openai_image",
            side_effect=finish_old_image,
        ):
            generate_reference(
                character.pk, character.job_id, character.generation_brief()
            )
        character.refresh_from_db()
        self.assertEqual(character.appearance, "Blue fox")
        self.assertEqual(character.status, "FAILED")
        self.assertFalse(character.image)
        self.assertEqual(MediaAsset.objects.filter(created_by=self.user).count(), 1)
