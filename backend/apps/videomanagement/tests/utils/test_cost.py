from django.test import TestCase

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import scene, scene_image, twitch_video, video
from ...utils.cost_utils import calculate_total_cost, charge_user


class CalculateTotalCostTests(TestCase):
    def setUp(self):
        self.video = video.make(mode="WEB")

    def add_scenes(self, count, with_images=0):
        scenes = scene.make(video=self.video, _quantity=count)
        for line in scenes[:with_images]:
            scene_image.make(scene=line)

        return scenes

    def test_charges_the_base_rate_plus_a_rate_per_scene_and_per_image(self):
        self.add_scenes(2, with_images=2)
        self.assertAlmostEqual(calculate_total_cost(self.video), 0.24)

    def test_does_not_charge_for_a_scene_image_that_was_never_generated(self):
        self.add_scenes(1)
        scene_image.make(
            scene=self.video.scenes.first(),
            file=None,
        )

        self.assertAlmostEqual(calculate_total_cost(self.video), 0.14)

    def test_charges_the_ai_image_rate_for_an_ai_video(self):
        self.video.mode = "AI"
        self.add_scenes(1, with_images=1)

        self.assertAlmostEqual(calculate_total_cost(self.video), 0.22)

    def test_charges_the_twitch_rate_per_clip(self):
        clips = twitch_video.make()
        scene.make(video=clips, _quantity=3)

        self.assertAlmostEqual(calculate_total_cost(clips), 0.05 + 3 * 0.08)

    def test_costs_nothing_before_any_scene_exists(self):
        self.assertAlmostEqual(calculate_total_cost(self.video), 0.12)


class ChargeUserTests(TestCase):
    def setUp(self):
        self.user = user.make(generation_limit_for_ai=10)
        self.video = video.make(created_by=self.user, mode="WEB")

    def test_deducts_the_videos_cost_and_refreshes_the_in_memory_balance(self):
        charged = charge_user(self.user, "generation_limit_for_ai", self.video)

        self.assertAlmostEqual(charged, 0.12)
        self.assertAlmostEqual(self.user.generation_limit_for_ai, 9.88)

    def test_writes_the_deduction_in_the_database_rather_than_the_whole_row(self):
        stale = type(self.user).objects.get(pk=self.user.pk)

        charge_user(self.user, "generation_limit_for_ai", self.video)
        charge_user(stale, "generation_limit_for_ai", self.video)

        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.generation_limit_for_ai, 10 - 0.24)

    def test_does_not_charge_a_video_with_no_owner(self):
        self.assertEqual(charge_user(None, "generation_limit_for_ai", self.video), 0)
