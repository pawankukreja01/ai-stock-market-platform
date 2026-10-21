
from decimal import Decimal
from unittest import TestCase

from market_data.recommendation_allocation import allocate_whole_shares


class RankingFirstAllocationTests(TestCase):
    def setUp(self):
        self.candidates = [
            {
                "symbol": "AAA",
                "company_name": "First Ranked",
                "currency": "USD",
                "latest_price": "600.00",
                "rank": 1,
                "score": 90.0,
            },
            {
                "symbol": "BBB",
                "company_name": "Second Ranked",
                "currency": "USD",
                "latest_price": "250.00",
                "rank": 2,
                "score": 80.0,
            },
            {
                "symbol": "CCC",
                "company_name": "Third Ranked",
                "currency": "USD",
                "latest_price": "100.00",
                "rank": 3,
                "score": 70.0,
            },
        ]

    def allocate(self, candidates=None, **kwargs):
        options = {
            "budget": Decimal("1000.00"),
            "currency": "USD",
            "max_allocations": 10,
        }
        options.update(kwargs)

        return allocate_whole_shares(
            self.candidates if candidates is None else candidates,
            **options,
        )

    def test_allocates_to_candidates_in_ranking_order(self):
        result = self.allocate()

        self.assertEqual(
            [item["symbol"] for item in result["allocations"]],
            ["AAA", "BBB", "CCC"],
        )
        self.assertEqual(
            [item["shares"] for item in result["allocations"]],
            [1, 1, 1],
        )
        self.assertEqual(result["invested"], "950.00")
        self.assertEqual(result["remaining_cash"], "50.00")

    def test_highest_ranked_stock_gets_shares_first(self):
        candidates = [
            {
                "symbol": "AAA",
                "currency": "USD",
                "latest_price": "100.00",
                "rank": 1,
                "score": 90.0,
            },
            {
                "symbol": "BBB",
                "currency": "USD",
                "latest_price": "50.00",
                "rank": 2,
                "score": 80.0,
            },
        ]

        result = self.allocate(candidates)

        self.assertEqual(
            [(item["symbol"], item["shares"])
             for item in result["allocations"]],
            [("AAA", 10)],
        )
        self.assertEqual(result["invested"], "1000.00")
        self.assertEqual(result["remaining_cash"], "0.00")

    def test_never_exceeds_budget(self):
        result = self.allocate()

        invested = Decimal(result["invested"])
        remaining = Decimal(result["remaining_cash"])
        budget = Decimal(result["budget"])

        self.assertLessEqual(invested, budget)
        self.assertGreaterEqual(remaining, Decimal("0"))
        self.assertEqual(invested + remaining, budget)

    def test_all_allocations_use_whole_shares(self):
        result = self.allocate()

        self.assertFalse(result["fractional_shares_used"])

        for item in result["allocations"]:
            self.assertIsInstance(item["shares"], int)
            self.assertGreater(item["shares"], 0)
            self.assertEqual(
                Decimal(item["estimated_cost"]),
                Decimal(item["latest_price"]) * item["shares"],
            )

    def test_excludes_unknown_or_mismatched_currency(self):
        candidates = [
            {
                "symbol": "AAA",
                "currency": "GBP",
                "latest_price": "100.00",
                "rank": 1,
            },
            {
                "symbol": "BBB",
                "currency": None,
                "latest_price": "100.00",
                "rank": 2,
            },
            {
                "symbol": "CCC",
                "currency": "USD",
                "latest_price": "100.00",
                "rank": 3,
            },
        ]

        result = self.allocate(candidates)

        self.assertEqual(
            [item["symbol"] for item in result["allocations"]],
            ["CCC"],
        )
        self.assertEqual(
            [item["symbol"] for item in result["excluded"]],
            ["AAA", "BBB"],
        )
        self.assertEqual(result["invested"], "1000.00")
        self.assertEqual(result["remaining_cash"], "0.00")

    def test_excludes_invalid_prices(self):
        candidates = [
            {
                "symbol": "AAA",
                "currency": "USD",
                "latest_price": "0",
                "rank": 1,
            },
            {
                "symbol": "BBB",
                "currency": "USD",
                "latest_price": "not-a-price",
                "rank": 2,
            },
            {
                "symbol": "CCC",
                "currency": "USD",
                "latest_price": "100.00",
                "rank": 3,
            },
        ]

        result = self.allocate(candidates)

        self.assertEqual(
            [item["symbol"] for item in result["allocations"]],
            ["CCC"],
        )
        self.assertEqual(
            [item["symbol"] for item in result["excluded"]],
            ["AAA", "BBB"],
        )

    def test_no_candidates_returns_full_budget_as_cash(self):
        result = self.allocate([])

        self.assertEqual(result["allocations"], [])
        self.assertEqual(result["excluded"], [])
        self.assertEqual(result["invested"], "0.00")
        self.assertEqual(result["remaining_cash"], "1000.00")

    def test_rejects_invalid_budget(self):
        for budget in ("invalid", "0", "-1", "NaN", "Infinity"):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    self.allocate(budget=budget)

    def test_rejects_invalid_currency(self):
        for currency in ("US", "USDD", "U$D", "ÜSD", ""):
            with self.subTest(currency=currency):
                with self.assertRaises(ValueError):
                    self.allocate(currency=currency)

    def test_rejects_invalid_allocation_limit(self):
        for limit in (0, -1, 101, 1.5, True):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    self.allocate(max_allocations=limit)
