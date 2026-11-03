import json
from pathlib import Path

from django.test import SimpleTestCase

from apps.videomanagement.serializers.overlays import OverlaySerializer, SceneOverlaysSerializer
from apps.videomanagement.utils.diagrams import diagram_plan
from apps.videomanagement.utils.composer.diagrams import diagram_overlays


class DiagramRenderTests(SimpleTestCase):
    def test_geometry_matches_browser_fixtures_and_stays_caption_safe(self):
        rows = json.loads(Path(__file__).with_name("diagram_fixtures.json").read_text())
        for row in rows:
            with self.subTest(template=row["diagram"]["template"], size=row["size"]):
                plan = diagram_plan(row["diagram"], row["size"], row["duration"])
                self.assertEqual(plan, row["plan"])
                for element in plan[1:]:
                    self.assertGreaterEqual(element["x"], 0)
                    self.assertLess(element["y"], row["size"][1] * .8)
                    self.assertLess(element["start"], row["duration"])

    def test_render_escapes_user_text_and_offsets_scene_timing(self):
        serializer = OverlaySerializer(data={"kind": "diagram", "diagram": {
            "template": "comparison", "items": [
                {"label": r"{\move(0,0,999,999)}", "detail": "Before"},
                {"label": "After", "detail": "Changed"},
            ],
        }})
        serializer.is_valid(raise_exception=True)
        styles, events = diagram_overlays(serializer.validated_data, "Diagram", (1080, 1920), 10, 14)
        self.assertTrue(styles)
        self.assertIn("0:00:12.60", "\n".join(events))
        self.assertNotIn(r"{\move(0,0,999,999)}", "\n".join(events))
        self.assertIn(r"\t(0,320,\fscx100)", "\n".join(events))

    def test_diagram_contents_are_bounded_and_cannot_stack(self):
        item = {"kind": "diagram", "diagram": {"template": "steps", "items": [{"label": "One"}, {"label": "Two"}]}}
        self.assertTrue(SceneOverlaysSerializer(data={"overlays": [item]}).is_valid())
        for diagram in (
            {}, {"template": "unsupported", "items": [{"label": "One"}] * 2},
            {"template": "steps", "items": [{"label": ""}] * 2},
            {"template": "steps", "items": [{"label": "x" * 41}] * 2},
            {"template": "steps", "items": [{"label": "One"}] * 5},
            {"template": "comparison", "items": [{"label": "One"}] * 3},
        ):
            self.assertFalse(OverlaySerializer(data={"kind": "diagram", "diagram": diagram}).is_valid(), diagram)
        self.assertFalse(SceneOverlaysSerializer(data={"overlays": [item, item]}).is_valid())
