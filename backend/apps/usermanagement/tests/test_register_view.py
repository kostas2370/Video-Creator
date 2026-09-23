from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from ..baker_recipes import user
from ..models import User

PASSWORD = "a-Very-Good-1"


@override_settings(USER_LIMIT=10)
class UserRegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, **overrides):
        data = {
            "username": "ada",
            "email": "ada@example.test",
            "password": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse("register"), data)

    def test_creates_the_account_and_answers_with_it(self):
        response = self.register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "ada")
        self.assertTrue(User.objects.filter(email="ada@example.test").exists())

    def test_never_writes_the_password_into_the_answer(self):
        self.assertNotIn("password", self.register().data)

    def test_stores_the_password_hashed_so_the_account_can_sign_in(self):
        self.register()

        created = User.objects.get(username="ada")
        self.assertNotEqual(created.password, PASSWORD)
        self.assertTrue(created.check_password(PASSWORD))

    def test_leaves_the_account_unverified_until_the_link_is_followed(self):
        self.register()

        self.assertFalse(User.objects.get(username="ada").is_verified)

    def test_emails_a_verification_link_that_points_at_the_verify_route(self):
        self.register()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.test"])
        self.assertIn(f"{reverse('email-verify')}?token=", mail.outbox[0].body)

    def test_turns_away_a_password_that_breaks_the_rules(self):
        response = self.register(password="weak")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="ada").exists())

    def test_turns_away_an_email_another_account_already_holds(self):
        user.make(email="ada@example.test")

        response = self.register()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(email="ada@example.test").count(), 1)

    def test_turns_away_a_username_another_account_already_holds(self):
        user.make(username="ada")

        response = self.register()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.filter(username="ada").count(), 1)

    def test_sends_no_mail_when_the_account_was_not_created(self):
        self.register(password="weak")

        self.assertEqual(mail.outbox, [])

    @override_settings(USER_LIMIT=0)
    def test_stops_signing_people_up_once_the_limit_is_reached(self):
        user.make()

        response = self.register()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.data["message"], "User limit reached, contact the admin !"
        )
        self.assertFalse(User.objects.filter(username="ada").exists())

    @override_settings(USER_LIMIT=1)
    def test_counts_the_last_seat_as_taken(self):
        user.make()

        self.assertEqual(self.register().status_code, 403)

    def test_is_open_to_a_caller_who_is_not_signed_in(self):
        self.assertEqual(self.register().status_code, 201)
