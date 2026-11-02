import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from django.test import SimpleTestCase

from ...serializers.overlays import OverlaySerializer
from ...utils.composer.overlays import text_overlay
from ...utils.photo_animation import animation_plan


class PhotoAnimationTests(SimpleTestCase):
    def test_editor_and_export_build_the_same_plans(self):
        fixtures = json.loads(Path(__file__).with_name("photo_animation_fixtures.json").read_text())
        for row in fixtures:
            with self.subTest(preset=row["preset"], intensity=row["intensity"]):
                scene = SimpleNamespace(
                    pk=UUID(row["id"]), animation_preset=row["preset"],
                    motion_intensity=row["intensity"], animation_accents=row["accents"],
                )
                self.assertEqual(animation_plan(scene), row["plan"])

    def test_watermarks_remain_static_and_user_text_cannot_inject_animation(self):
        for kind in ("title", "watermark", "arrow"):
            serializer = OverlaySerializer(data={"kind": kind, "text": r"{\move(0,0,999,999)}"})
            serializer.is_valid(raise_exception=True)
            _, event = text_overlay(serializer.validated_data, "Test", (1080, 1920), 0, .1, "PLAYFUL")
            self.assertNotIn(r"{\move(0,0,999,999)}", event)
            self.assertEqual(r"\t(" in event, kind != "watermark")
