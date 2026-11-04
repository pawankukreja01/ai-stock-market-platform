"""Budget, currency, position and sector guardrails for research-only portfolios."""
from decimal import Decimal
from django.test import SimpleTestCase
from market_data.recommendation_diversification import allocate_diversified_shares


def candidate(symbol, *, price="50", sector="Technology", currency="USD"):
    return {
        "symbol": symbol, "company_name": symbol,
        "exchange": "NASDAQ", "sector": sector,
        "currency": currency, "latest_price": price,
        "rank": len(symbol), "score": 75,
    }


class DiversifiedAllocationTests(SimpleTestCase):
    def test_spreads_initial_shares_and_caps_stock_and_sector_exposure(self):
        stocks = [
            candidate("AAA", sector="Technology"),
            candidate("BBB", sector="Technology"),
            candidate("CCC", sector="Energy"),
            candidate("DDD", sector="Healthcare"),
            candidate("EEE", sector="Industrials"),
        ]
        result = allocate_diversified_shares(
            stocks, budget="1000.00", currency="USD", risk_tolerance="moderate"
        )
        allocations = result["allocations"]
        self.assertGreaterEqual(len(allocations), 4)
        self.assertEqual(result["position_cap_percent"], 25)
        self.assertEqual(result["sector_cap_percent"], 50)
        self.assertEqual(result["method"], "diversified_caps_v1")
        self.assertEqual(
            Decimal(result["invested"]) + Decimal(result["remaining_cash"]),
            Decimal(result["budget"]),
        )
        for item in allocations:
            self.assertLessEqual(Decimal(item["estimated_cost"]), Decimal("250"))
            self.assertGreater(item["shares"], 0)
            self.assertEqual(item["shares"], int(item["shares"]))
        for amount in result["sector_exposure"].values():
            self.assertLessEqual(Decimal(amount), Decimal("500"))

    def test_single_stock_cannot_consume_entire_budget(self):
        result = allocate_diversified_shares(
            [candidate("AAA", price="100")], budget="1000",
            currency="USD", risk_tolerance="moderate"
        )
        self.assertEqual(result["allocations"][0]["shares"], 2)
        self.assertEqual(result["invested"], "200")
        self.assertEqual(result["remaining_cash"], "800")

    def test_expensive_share_is_not_bought_if_it_violates_position_cap(self):
        result = allocate_diversified_shares(
            [candidate("AAA", price="300")], budget="1000",
            currency="USD", risk_tolerance="moderate"
        )
        self.assertEqual(result["allocations"], [])
        self.assertEqual(result["remaining_cash"], "1000")
        self.assertIn("concentration", result["excluded"][0]["reason"])

    def test_unknown_sector_is_a_shared_exposure_bucket(self):
        result = allocate_diversified_shares(
            [candidate("AAA", sector=""), candidate("BBB", sector=""),
             candidate("CCC", sector="")],
            budget="1000", currency="USD", risk_tolerance="moderate"
        )
        self.assertLessEqual(Decimal(result["sector_exposure"]["Unknown"]), Decimal("500"))

    def test_mismatched_currency_and_invalid_price_excluded(self):
        result = allocate_diversified_shares(
            [candidate("AAA", currency="GBP"),
             candidate("BBB", price="NaN"),
             candidate("CCC", price="-4")],
            budget="1000", currency="USD"
        )
        self.assertEqual(len(result["excluded"]), 3)
        self.assertEqual(result["allocations"], [])

    def test_all_risk_profiles_preserve_cash_and_caps(self):
        stocks = [candidate(str(i), sector=f"S{i % 3}", price="13.45")
                  for i in range(15)]
        for risk in ("low", "moderate", "high"):
            result = allocate_diversified_shares(
                stocks, budget="1234.67", currency="USD",
                risk_tolerance=risk,
            )
            self.assertEqual(
                Decimal(result["invested"]) + Decimal(result["remaining_cash"]),
                Decimal("1234.67"),
            )
            limit = Decimal(result["budget"]) * Decimal(
                result["position_cap_percent"]
            ) / Decimal("100")
            for item in result["allocations"]:
                self.assertLessEqual(Decimal(item["estimated_cost"]), limit)

    def test_invalid_inputs_rejected(self):
        for budget in ("NaN", "-1", "0", "nan"):
            with self.assertRaises(ValueError):
                allocate_diversified_shares([], budget=budget, currency="USD")
        for currency in ("U$D", "US", "GBPZ", ""):
            with self.assertRaises(ValueError):
                allocate_diversified_shares([], budget=100, currency=currency)
        for tolerance in ("unknown", None, ""):
            with self.assertRaises(ValueError):
                allocate_diversified_shares(
                    [], budget=100, currency="USD", risk_tolerance=tolerance
                )
