from django.test import SimpleTestCase

from ..utils import check_conditions


class CheckConditionsTests(SimpleTestCase):
    def test_accepts_a_password_that_meets_every_rule(self):
        self.assertTrue(check_conditions("Password1"))

    def test_rejects_a_password_with_no_uppercase(self):
        self.assertFalse(check_conditions("password1"))

    def test_rejects_a_password_with_no_lowercase(self):
        self.assertFalse(check_conditions("PASSWORD1"))

    def test_rejects_a_password_with_no_digit(self):
        self.assertFalse(check_conditions("Passwordd"))

    def test_rejects_a_password_that_is_too_short(self):
        self.assertFalse(check_conditions("Pass1"))

    def test_rejects_an_empty_password(self):
        self.assertFalse(check_conditions(""))
