from unittest.mock import patch

from django.test import TestCase

from apps.usermanagement.baker_recipes import user

from ..models import ApiKeys, Provider


class VoiceKeyChangeTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.keys = ApiKeys.objects.create(user=self.user)

    def save_with(self, **changes):
        for field, value in changes.items():
            setattr(self.keys, field, value)

        with patch("apps.videomanagement.tasks.import_user_voices.delay") as queued:
            with self.captureOnCommitCallbacks(execute=True):
                self.keys.save()

        return queued

    def test_imports_the_voices_behind_a_new_elevenlabs_key(self):
        queued = self.save_with(elevenlabs_key="xi-key")

        queued.assert_called_once_with(self.user.id, Provider.ELEVENLABS)

    def test_imports_the_voices_behind_a_new_60db_key(self):
        queued = self.save_with(sixtydb_key="60db-key")

        queued.assert_called_once_with(self.user.id, Provider.SIXTYDB)

    def test_imports_from_both_providers_when_both_keys_arrive_at_once(self):
        queued = self.save_with(elevenlabs_key="xi-key", sixtydb_key="60db-key")

        self.assertEqual(
            sorted(call.args[1] for call in queued.call_args_list),
            sorted([Provider.ELEVENLABS, Provider.SIXTYDB]),
        )

    def test_imports_again_when_the_key_is_replaced(self):
        self.save_with(elevenlabs_key="xi-key")
        self.keys.refresh_from_db()

        self.save_with(elevenlabs_key="xi-other-key").assert_called_once()

    def test_imports_nothing_when_the_key_was_not_touched(self):
        self.save_with(elevenlabs_key="xi-key")
        self.keys.refresh_from_db()

        self.save_with(openai_key="sk-new").assert_not_called()

    def test_imports_nothing_when_a_voice_key_is_cleared(self):
        self.save_with(elevenlabs_key="xi-key")
        self.keys.refresh_from_db()

        self.save_with(elevenlabs_key="").assert_not_called()

    def test_imports_nothing_for_a_key_that_drives_no_voices(self):
        self.save_with(midjourney_key="mj-key").assert_not_called()
