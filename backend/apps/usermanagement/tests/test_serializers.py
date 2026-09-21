from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from ..baker_recipes import unverified_user, user
from ..serializers import (
    CookieTokenRefreshSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)

PASSWORD = "a-Very-Good-1"


class RegisterSerializerTests(TestCase):
    def valid(self, **overrides):
        data = {
            "username": "ada",
            "email": "ada@example.test",
            "password": PASSWORD,
        }
        data.update(overrides)
        return RegisterSerializer(data=data)

    def test_accepts_an_account_with_a_strong_password(self):
        self.assertTrue(self.valid().is_valid())

    def test_turns_away_a_password_that_breaks_the_rules(self):
        serializer = self.valid(password="weak")

        with self.assertRaises(AuthenticationFailed):
            serializer.is_valid()

    def test_needs_a_username_an_email_and_a_password(self):
        serializer = RegisterSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"username", "email", "password"})

    def test_rejects_an_email_another_account_already_holds(self):
        user.make(email="ada@example.test")

        self.assertFalse(self.valid().is_valid())

    def test_never_echoes_the_password_back(self):
        serializer = self.valid()
        serializer.is_valid()

        self.assertNotIn("password", serializer.data)


class UserSerializerTests(TestCase):
    def test_describes_the_account_without_its_password(self):
        data = UserSerializer(user.make(username="ada")).data

        self.assertEqual(data["username"], "ada")
        self.assertNotIn("password", data)


class LoginSerializerTests(TestCase):
    def setUp(self):
        self.user = user.make()
        self.user.set_password(PASSWORD)
        self.user.save()
        self.context = {"request": APIRequestFactory().post("/")}

    def serializer(self, **overrides):
        data = {"username": self.user.username, "password": PASSWORD}
        data.update(overrides)
        return LoginSerializer(data=data, context=self.context)

    def test_hands_back_a_token_pair_for_the_right_credentials(self):
        serializer = self.serializer()

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            AccessToken(serializer.validated_data["tokens"]["access"])["user_id"],
            self.user.id,
        )

    def test_turns_away_a_request_with_no_username(self):
        self.assertFalse(self.serializer(username="").is_valid())

    def test_turns_away_the_wrong_password(self):
        with self.assertRaises(AuthenticationFailed):
            self.serializer(password="not-the-password").is_valid()

    def test_turns_away_a_username_no_account_holds(self):
        with self.assertRaises(AuthenticationFailed):
            self.serializer(username="nobody").is_valid()

    def test_turns_away_an_account_that_was_never_verified(self):
        pending = unverified_user.make()
        pending.set_password(PASSWORD)
        pending.save()

        with self.assertRaises(AuthenticationFailed):
            self.serializer(username=pending.username).is_valid()

    def test_carries_the_remember_me_choice_through(self):
        serializer = self.serializer(remember_me=True)
        serializer.is_valid()

        self.assertTrue(serializer.validated_data["remember_me"])
        self.assertTrue(
            RefreshToken(serializer.validated_data["tokens"]["refresh"])["remember_me"]
        )

    def test_is_not_remembered_unless_it_was_asked_for(self):
        serializer = self.serializer()
        serializer.is_valid()

        self.assertFalse(serializer.validated_data["remember_me"])

    def test_never_writes_the_credentials_into_the_answer(self):
        serializer = self.serializer()
        serializer.is_valid()

        self.assertEqual(set(serializer.data), {"tokens"})


class CookieTokenRefreshSerializerTests(TestCase):
    def serializer(self, **cookies):
        request = APIRequestFactory().post("/")
        request.COOKIES = cookies
        return CookieTokenRefreshSerializer(data={}, context={"request": request})

    def test_reads_the_refresh_token_out_of_the_cookie(self):
        account = user.make()
        serializer = self.serializer(refresh_token=str(RefreshToken.for_user(account)))

        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            AccessToken(serializer.validated_data["access"])["user_id"], account.id
        )

    def test_refuses_a_request_that_carries_no_cookie(self):
        with self.assertRaises(InvalidToken):
            self.serializer().is_valid()

    def test_refuses_a_cookie_it_cannot_read(self):
        with self.assertRaises(TokenError):
            self.serializer(refresh_token="not-a-token").is_valid()
