from django.urls import reverse
from model_bakery.recipe import seq

from apps.usermanagement.baker_recipes import user
from ...baker_recipes import avatar, intro, outro, template_prompt, voice_model
from .base import ApiTestCase


class AssetPaginationTests(ApiTestCase):
    def test_all_libraries_are_bounded_and_later_pages_have_distinct_items(self):
        resources = (
            ("avatar", avatar), ("intro", intro), ("outro", outro),
            ("templateprompt", template_prompt), ("voicemodel", voice_model),
        )
        for resource, recipe in resources:
            with self.subTest(resource=resource):
                url = reverse(resource + "-list")
                existing_count = self.client.get(url).data["count"]
                fields = {"title": seq("Template ")} if resource == "templateprompt" else {}
                recipe.make(created_by=self.user if resource != "voicemodel" else None, _quantity=30, **fields)
                first = self.client.get(url)
                second = self.client.get(url, {"page": 2})
                self.assertEqual(first.status_code, 200)
                self.assertEqual(first.data["count"], existing_count + 30)
                self.assertEqual(len(first.data["results"]), 24)
                self.assertEqual(first.data["next"], 2)
                self.assertEqual(len(second.data["results"]), existing_count + 6)
                self.assertEqual(second.data["previous"], 1)
                self.assertIsNone(second.data["next"])
                self.assertFalse({row["id"] for row in first.data["results"]} & {row["id"] for row in second.data["results"]})

    def test_page_size_has_a_hard_cap_and_foreign_assets_are_not_counted(self):
        avatar.make(created_by=self.user, _quantity=105)
        avatar.make(created_by=user.make(), _quantity=2)
        response = self.client.get(reverse("avatar-list"), {"page_size": 10000})
        self.assertEqual(response.data["count"], 105)
        self.assertEqual(len(response.data["results"]), 100)
        self.assertEqual(response.data["next"], 2)

    def test_video_lists_also_have_a_hard_cap(self):
        for _ in range(105):
            self.video_for()
        response = self.client.get(reverse("video-list"), {"page_size": 10000})
        self.assertEqual(len(response.data["results"]), 100)
        self.assertEqual(response.data["next"], 2)

    def test_asset_search_applies_before_pagination(self):
        avatar.make(created_by=self.user, name="Unrelated", _quantity=25)
        selected = avatar.make(created_by=self.user, name="Selected presenter")
        response = self.client.get(reverse("avatar-list"), {"search": "Selected"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual([row["id"] for row in response.data["results"]], [str(selected.pk)])
