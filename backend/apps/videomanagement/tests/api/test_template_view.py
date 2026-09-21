from django.urls import reverse

from apps.usermanagement.baker_recipes import user

from ...baker_recipes import template_prompt
from ...models import TemplatePrompt
from .base import ApiTestCase


class TemplateApiTestCase(ApiTestCase):
    def save(self, **overrides):
        payload = {"title": "Shorts", "message": "make me a short", "image_mode": "AI"}
        payload.update(overrides)

        return self.client.post(reverse("templateprompt-list"), payload, format="json")


class SaveTemplateTests(TemplateApiTestCase):
    def test_keeps_the_saved_preset_against_the_caller(self):
        response = self.save()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            TemplatePrompt.objects.get(title="Shorts").created_by, self.user
        )

    def test_the_caller_can_see_what_they_just_saved(self):
        self.save()

        listed = self.client.get(reverse("templateprompt-list")).data

        self.assertEqual([t["title"] for t in listed], ["Shorts"])

    def test_a_preset_cannot_be_saved_against_somebody_else(self):
        stranger = user.make()

        self.save(created_by=stranger.id)

        self.assertEqual(
            TemplatePrompt.objects.get(title="Shorts").created_by, self.user
        )

    def test_two_people_can_each_keep_a_preset_of_the_same_name(self):
        template_prompt.make(title="Shorts", created_by=user.make())

        self.assertEqual(self.save().status_code, 201)

    def test_refuses_a_name_the_caller_has_already_used(self):
        self.save()

        response = self.save(message="a different prompt")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(TemplatePrompt.objects.filter(title="Shorts").count(), 1)

    def test_keeps_the_settings_the_preset_was_saved_with(self):
        self.save(style="vivid", subtitles=False, avatar_position="left,top")

        saved = TemplatePrompt.objects.get(title="Shorts")
        self.assertEqual(saved.image_mode, "AI")
        self.assertEqual(saved.style, "vivid")
        self.assertFalse(saved.subtitles)
        self.assertEqual(saved.avatar_position, "left,top")

    def test_saves_a_preset_that_picked_no_avatar(self):
        response = self.save(avatar_selection="", voice_id="")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(TemplatePrompt.objects.get(title="Shorts").avatar_selection)


class DeleteTemplateTests(TemplateApiTestCase):
    def delete(self, template):
        return self.client.delete(reverse("templateprompt-detail", args=[template.id]))

    def test_the_owner_can_throw_their_preset_away(self):
        mine = template_prompt.make(title="Shorts", created_by=self.user)

        self.assertEqual(self.delete(mine).status_code, 204)
        self.assertFalse(TemplatePrompt.objects.filter(pk=mine.pk).exists())

    def test_a_stranger_cannot_throw_it_away(self):
        theirs = template_prompt.make(title="Shorts", created_by=user.make())

        self.assertEqual(self.delete(theirs).status_code, 404)
        self.assertTrue(TemplatePrompt.objects.filter(pk=theirs.pk).exists())

    def test_the_name_is_free_again_afterwards(self):
        mine = template_prompt.make(title="Shorts", created_by=self.user)
        self.delete(mine)

        self.assertEqual(self.save().status_code, 201)
