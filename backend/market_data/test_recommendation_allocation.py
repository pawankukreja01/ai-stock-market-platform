
from decimal import Decimal

from django.test import SimpleTestCase

from .recommendation_allocation import allocate_whole_shares


class RecommendationAllocationTests(SimpleTestCase):
    def setUp(self):
        self.candidates = [
            {
                "symbol": "AAA",
                "company_name": "Example A",
                "exchange": "NASDAQ",
                "currency": "USD",
                "latest_price": "100.00",
                "rank": 1,
                "score": 90,
            },
            {
                "symbol": "BBB",
                "company_name": "Example B",
                "exchange": "NASDAQ",
                "currency": "USD",
                "latest_price": "60.00",
                "rank": 2,
                "score": 80,
            },
        ]

    def test_allocation_never_exceeds_budget(self):
        result = allocate_whole_shares(
            self.candidates,
            budget="1000.00",
            currency="USD",
        )

        self.assertLessEqual(
            Decimal(result["invested"]),
            Decimal(result["budget"]),
        )
        self.assertEqual(
            Decimal(result["invested"])
            + Decimal(result["remaining_cash"]),
            Decimal(result["budget"]),
        )

    def test_unknown_or_mismatched_currency_is_excluded(self):
        candidates = [
            {**self.candidates[0], "currency": None},
            {**self.candidates[1], "currency": "GBP"},
        ]

        result = allocate_whole_shares(
            candidates,
            budget="1000",
            currency="USD",
        )

        self.assertEqual(result["allocations"], [])
        self.assertEqual(len(result["excluded"]), 2)
        self.assertEqual(result["remaining_cash"], "1000")

    def test_budget_too_small_for_one_share(self):
        result = allocate_whole_shares(
            self.candidates,
            budget="10",
            currency="USD",
        )

        self.assertEqual(result["allocations"], [])
        self.assertEqual(result["remaining_cash"], "10")

    def test_invalid_price_is_excluded(self):
        candidate = {**self.candidates[0], "latest_price": None}

        result = allocate_whole_shares(
            [candidate],
            budget="1000",
            currency="USD",
        )

        self.assertEqual(result["allocations"], [])
        self.assertIn("price", result["excluded"][0]["reason"].lower())

    def test_only_whole_shares_are_allocated(self):
        result = allocate_whole_shares(
            self.candidates,
            budget="250",
            currency="USD",
        )

        for allocation in result["allocations"]:
            self.assertIsInstance(allocation["shares"], int)
            self.assertGreater(allocation["shares"], 0)

        self.assertFalse(result["fractional_shares_used"])
