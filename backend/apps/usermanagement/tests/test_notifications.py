from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.videomanagement.baker_recipes import video
from apps.videomanagement.models import Video
from apps.videomanagement.tasks import reap_stalled_videos, render_video_task

from ..baker_recipes import user
from ..models import Notification


class NotificationApiTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def notify(self, owner=None, **kwargs):
        fields = dict(title="Video Completed", message="ready", link="/videos/1/")
        fields.update(kwargs)
        return Notification.objects.create(user=owner or self.user, **fields)

    def list(self):
        return self.client.get(reverse("notification-list")).data

    def test_hands_back_what_the_caller_has_been_told(self):
        self.notify(title="Video Completed")

        listed = self.list()

        self.assertEqual([n["title"] for n in listed["results"]], ["Video Completed"])
        self.assertEqual(listed["unread"], 1)

    def test_never_shows_another_persons_notifications(self):
        self.notify(owner=user.make(), title="Not yours")

        self.assertEqual(self.list()["results"], [])

    def test_counts_only_the_unread_ones(self):
        self.notify()
        self.notify(read=True)

        self.assertEqual(self.list()["unread"], 1)

    def test_newest_first(self):
        self.notify(title="older")
        self.notify(title="newer")

        self.assertEqual(
            [n["title"] for n in self.list()["results"]], ["newer", "older"]
        )

    def test_one_can_be_marked_read(self):
        notification = self.notify()

        response = self.client.patch(
            reverse("notification-detail", args=[notification.id]),
            {"read": True},
            format="json",
        )

        notification.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(notification.read)

    def test_a_stranger_cannot_mark_one_read(self):
        theirs = self.notify(owner=user.make())

        response = self.client.patch(
            reverse("notification-detail", args=[theirs.id]),
            {"read": True},
            format="json",
        )

        theirs.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertFalse(theirs.read)

    def test_they_can_all_be_marked_read_at_once(self):
        self.notify()
        self.notify()
        stranger = self.notify(owner=user.make())

        response = self.client.patch(reverse("notification-read-all"))

        stranger.refresh_from_db()
        self.assertEqual(response.data["read"], 2)
        self.assertEqual(self.list()["unread"], 0)
        self.assertFalse(stranger.read)

    def test_a_signed_out_visitor_is_told_nothing(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(reverse("notification-list")).status_code, 401)


class VideoNotificationTests(TestCase):
    def setUp(self):
        self.owner = user.make()
        self.video = video.make(created_by=self.owner, status="RENDERING")

    def settle(self, status, on=None):
        target = on or self.video
        target.status = status
        with self.captureOnCommitCallbacks(execute=True):
            target.save()

    def test_a_finished_video_tells_its_owner(self):
        self.settle("COMPLETED")

        notification = Notification.objects.get(user=self.owner)
        self.assertEqual(notification.title, "Video Completed")
        self.assertEqual(notification.link, f"/videos/{self.video.pk}/")
        self.assertFalse(notification.read)

    def test_a_failed_video_tells_its_owner(self):
        self.settle("FAILED")

        self.assertEqual(
            Notification.objects.get(user=self.owner).title, "Video Failed"
        )

    def test_nothing_is_recorded_while_the_video_is_still_being_worked_on(self):
        self.settle("GENERATION")

        self.assertFalse(Notification.objects.exists())

    def test_an_ownerless_video_tells_nobody(self):
        orphan = video.make(created_by=None, status="RENDERING")

        self.settle("COMPLETED", on=orphan)

        self.assertFalse(Notification.objects.exists())

    def test_a_video_a_worker_gave_up_on_tells_its_owner(self):
        with patch(
            "apps.videomanagement.utils.composer.render.make_video",
            side_effect=RuntimeError("the encoder died"),
        ):
            with self.assertRaises(RuntimeError):
                with self.captureOnCommitCallbacks(execute=True):
                    render_video_task(video_id=self.video.id)

        self.assertEqual(
            Notification.objects.get(user=self.owner).title, "Video Failed"
        )

    @override_settings(VIDEO_TASK_STALE_AFTER=3600)
    def test_a_reaped_video_tells_its_owner(self):
        Video.objects.filter(pk=self.video.pk).update(
            updated_at=timezone.now() - timedelta(seconds=7200)
        )

        with self.captureOnCommitCallbacks(execute=True):
            reap_stalled_videos()

        self.assertEqual(
            Notification.objects.get(user=self.owner).title, "Video Failed"
        )
