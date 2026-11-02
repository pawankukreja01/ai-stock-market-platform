from decimal import Decimal
from unittest import TestCase

from market_data.currency_utils import (
    CurrencyMetadataUnavailable,
    get_provider_currency_details,
    normalize_provider_currency,
    normalize_provider_price,
)


class ProviderCurrencyTests(TestCase):

    def test_gbp_pence_normalization(self):
        currency = normalize_provider_currency("GBp")

        self.assertEqual(currency.raw_code, "GBp")
        self.assertEqual(currency.storage_code, "GBP")
        self.assertEqual(
            currency.price_multiplier,
            Decimal("0.01"),
        )

        self.assertEqual(
            normalize_provider_price("1915", currency),
            Decimal("19.15"),
        )

    def test_gbx_pence_normalization(self):
        currency = normalize_provider_currency("GBX")

        self.assertEqual(currency.storage_code, "GBP")
        self.assertEqual(
            normalize_provider_price("1250", currency),
            Decimal("12.50"),
        )

    def test_gbp_pounds_are_not_converted(self):
        currency = normalize_provider_currency("GBP")

        self.assertEqual(currency.storage_code, "GBP")
        self.assertEqual(
            normalize_provider_price("19.15", currency),
            Decimal("19.15"),
        )

    def test_usd_is_not_converted(self):
        currency = normalize_provider_currency("USD")

        self.assertEqual(currency.storage_code, "USD")
        self.assertEqual(
            normalize_provider_price("33.83", currency),
            Decimal("33.83"),
        )

    def test_non_gbp_currency_is_preserved(self):
        currency = normalize_provider_currency("EUR")

        self.assertEqual(currency.storage_code, "EUR")
        self.assertEqual(
            normalize_provider_price("25.50", currency),
            Decimal("25.50"),
        )

    def test_invalid_currency_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_provider_currency("UNKNOWN")

    def test_empty_currency_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_provider_currency("")

    def test_fast_info_is_preferred(self):
        class FakeTicker:
            fast_info = {"currency": "GBp"}
            info = {"currency": "GBP"}

        result = get_provider_currency_details(FakeTicker())

        self.assertEqual(result.raw_code, "GBp")
        self.assertEqual(result.storage_code, "GBP")

    def test_info_is_used_as_fallback(self):
        class FakeTicker:
            fast_info = {}
            info = {"currency": "USD"}

        result = get_provider_currency_details(FakeTicker())

        self.assertEqual(result.storage_code, "USD")

    def test_missing_currency_fails_closed(self):
        class FakeTicker:
            fast_info = {}
            info = {}

        with self.assertRaises(CurrencyMetadataUnavailable):
            get_provider_currency_details(FakeTicker())