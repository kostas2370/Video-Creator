from unittest.mock import patch

from django.test import TestCase

from apps.usermanagement.baker_recipes import user

from ..baker_recipes import video


class VideoOwnerEmailTests(TestCase):
    def setUp(self):
        self.owner = user.make(email="owner@example.test")
        self.video = video.make(
            created_by=self.owner,
            status="RENDERING",
            title="Cats",
            url="https://a.test/x",
        )

    def settle(self, status, on=None):
        target = on or self.video
        target.status = status
        with patch("apps.videomanagement.models.send_email.delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                target.save()

        return send

    def test_tells_the_owner_their_video_is_ready(self):
        send = self.settle("COMPLETED")

        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["email"], "owner@example.test")
        self.assertEqual(send.call_args.kwargs["name"], "Video Completed")
        self.assertIn("https://a.test/x", send.call_args.kwargs["text"])

    def test_tells_the_owner_their_video_failed(self):
        send = self.settle("FAILED")

        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs["email"], "owner@example.test")
        self.assertEqual(send.call_args.kwargs["name"], "Video Failed")

    def test_says_nothing_while_the_video_is_still_being_worked_on(self):
        self.settle("GENERATION").assert_not_called()

    def test_does_not_mail_again_when_a_completed_video_is_saved(self):
        self.settle("COMPLETED")
        self.video.refresh_from_db()

        self.settle("COMPLETED").assert_not_called()

    def test_leaves_an_ownerless_video_alone(self):
        orphan = video.make(created_by=None, status="RENDERING")

        self.settle("COMPLETED", on=orphan).assert_not_called()
