from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings

from apps.usermanagement.baker_recipes import user

from ..baker_recipes import scene, scene_image, video, voice_model
from ..models import Video, VideoStatus, VideoType, VoiceModel


class ModelQuerySetTests(TestCase):
    def test_video_scopes_compose_without_exposing_other_owners(self):
        owner = user.make()
        manual = video.make(
            created_by=owner,
            video_type=VideoType.MANUAL,
            gpt_answer=None,
            status=VideoStatus.GENERATION,
        )
        scripted = video.make(
            created_by=owner,
            gpt_answer={"title": "Ready"},
            status=VideoStatus.COMPLETED,
        )
        video.make(created_by=owner, gpt_answer=None, status=VideoStatus.GENERATION)
        video.make(created_by=user.make(), video_type=VideoType.MANUAL)
        video.make(created_by=None, video_type=VideoType.MANUAL)
        visible = Video.objects.for_user(owner).listable()
        self.assertCountEqual(visible, [manual, scripted])
        self.assertEqual(list(visible.in_flight()), [manual])
        self.assertFalse(Video.objects.for_user(AnonymousUser()).exists())
        self.assertFalse(Video.objects.for_user(None).exists())
        self.assertFalse(visible.exclude(pk=manual.pk).in_flight().exists())

    def test_related_scene_queryset_preserves_scope_order_and_prefetches_media(self):
        project = video.make()
        first = scene.make(video=project)
        second = scene.make(video=project)
        scene_image.make(scene=first)
        scene_image.make(scene=second)
        scene_image.make(scene=scene.make(video=video.make()))
        with self.assertNumQueries(2):
            loaded = list(project.scenes.order_by("-position").with_media())
            self.assertEqual([item.pk for item in loaded], [second.pk, first.pk])
            self.assertEqual([len(item.scene_images.all()) for item in loaded], [1, 1])

    @override_settings(OPEN_API_KEY="service-key")
    def test_voice_availability_preserves_existing_queryset_filters(self):
        owner = user.make(use_service_api_keys=True)
        selected = voice_model.make(created_by=None, provider="OPENAI")
        voice_model.make(created_by=None, provider="OPENAI")
        voices = VoiceModel.objects.filter(pk=selected.pk).available_to(owner)
        self.assertEqual(list(voices), [selected])
        self.assertFalse(voices.exclude(pk=selected.pk).exists())
