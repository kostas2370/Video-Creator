from datetime import date
from unittest.mock import patch
from decimal import Decimal
import json
from pathlib import Path

from django.test import SimpleTestCase

from apps.usage import pricing


class PricingCatalogTests(SimpleTestCase):
    def setUp(self):
        self.catalog = json.loads(
            Path(pricing.__file__).with_name("pricing.json").read_text()
        )

    def assert_valid_price(self, value):
        self.assertIsInstance(value, str)
        amount = Decimal(value)
        self.assertTrue(amount.is_finite())
        self.assertGreaterEqual(amount, 0)
        return amount

    def test_catalog_has_currency_date_and_source_provenance(self):
        self.assertEqual(self.catalog["currency"], "USD")
        date.fromisoformat(self.catalog["checked_at"])
        for url in self.catalog["sources"].values():
            self.assertTrue(url.startswith("https://"))

    def test_every_rate_uses_nonnegative_decimal_strings_and_a_source(self):
        units = {
            "characters",
            "images",
            "seconds",
            "requests",
            "input_tokens",
            "output_tokens",
        }
        for key, rate in self.catalog["rates"].items():
            with self.subTest(rate=key):
                self.assertEqual(len(key.split(":")), 3)
                self.assertTrue(rate["source"].startswith("https://"))
                priced = units.intersection(rate)
                self.assertTrue(priced)
                for unit in priced:
                    self.assert_valid_price(rate[unit])

    def test_image_reference_ranges_and_token_rates_are_valid(self):
        for model, qualities in self.catalog["image_reference_prices"].items():
            for quality, prices in qualities.items():
                with self.subTest(model=model, quality=quality):
                    low = self.assert_valid_price(prices["low_usd"])
                    high = self.assert_valid_price(prices["high_usd"])
                    self.assertLessEqual(low, high)
        for rate in self.catalog["image_token_rates_per_million"].values():
            self.assertEqual(set(rate), {"text_input", "image_input", "image_output"})
            for value in rate.values():
                self.assert_valid_price(value)

    def test_gemini_promotional_prices_change_on_the_published_dates(self):
        for day, model, expected in (
            (date(2026, 11, 30), "gemini-4-argon", "0.000002"),
            (date(2026, 12, 1), "gemini-4-argon", "0.000004"),
            (date(2026, 12, 31), "gemini-3.8-flash", "0.00000075"),
            (date(2027, 1, 1), "gemini-3.8-flash", "0.0000015"),
        ):
            with (
                self.subTest(day=day, model=model),
                patch.object(pricing, "date") as clock,
            ):
                clock.today.return_value = day
                self.assertEqual(
                    pricing.rate_for("text", "GEMINI", model)["input_tokens"], expected
                )
