
from datetime import date
from decimal import Decimal

from django.test import TestCase

from stocks.models import Stock
from market_data.models import HistoricalPrice
from market_data.recommendation_services import (
    get_recommendation_candidates,
)


class RecommendationCandidateServiceTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="TEST",
            company_name="Test Company",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )

    def add_price(self, price_date, close_price):
        HistoricalPrice.objects.create(
            stock=self.stock,
            date=price_date,
            open_price=close_price,
            high_price=close_price,
            low_price=close_price,
            close_price=close_price,
            adjusted_close=close_price,
            volume=1000,
        )

    def test_latest_non_positive_close_is_skipped(self):
        self.add_price(date(2026, 1, 1), Decimal("100.00"))
        self.add_price(date(2026, 1, 2), Decimal("105.50"))
        HistoricalPrice.objects.create(
            stock=self.stock,
            date=date(2026, 1, 3),
            open_price=Decimal("0"),
            high_price=Decimal("0"),
            low_price=Decimal("0"),
            close_price=Decimal("0"),
            adjusted_close=Decimal("0"),
            volume=1000,
            is_ohlc_valid=False,
        )

        candidates = get_recommendation_candidates(market="NASDAQ", max_candidates=10)
        candidate = next(item for item in candidates if item["symbol"] == "TEST")

        self.assertEqual(candidate["latest_price"], "105.5000")
        self.assertEqual(candidate["latest_price_date"], "2026-01-02")

    def test_positive_close_is_not_excluded_for_invalid_ohlc_flag(self):
        self.add_price(date(2026, 1, 2), Decimal("105.50"))
        record = HistoricalPrice.objects.get(stock=self.stock, date=date(2026, 1, 2))
        record.is_ohlc_valid = False
        record.quality_flags = ["HIGH_BELOW_CLOSE"]
        record.save(update_fields=["is_ohlc_valid", "quality_flags"])

        candidates = get_recommendation_candidates(market="NASDAQ", max_candidates=10)
        candidate = next(item for item in candidates if item["symbol"] == "TEST")

        self.assertEqual(candidate["latest_price"], "105.5000")
        self.assertTrue(candidate["price_available"])

    def test_candidate_includes_latest_price(self):
        self.add_price(date(2026, 1, 1), Decimal("100.00"))
        self.add_price(date(2026, 1, 2), Decimal("105.50"))

        candidates = get_recommendation_candidates(
            market="NASDAQ",
            max_candidates=10,
        )

        candidate = next(
            item for item in candidates
            if item["symbol"] == "TEST"
        )

        self.assertEqual(candidate["latest_price"], "105.5000")
        self.assertEqual(
            candidate["latest_price_date"],
            "2026-01-02",
        )
        self.assertTrue(candidate["price_available"])

    def test_missing_price_is_not_fabricated(self):
        candidates = get_recommendation_candidates(
            market="NASDAQ",
            max_candidates=10,
        )

        candidate = next(
            item for item in candidates
            if item["symbol"] == "TEST"
        )

        self.assertIsNone(candidate["latest_price"])
        self.assertIsNone(candidate["latest_price_date"])
        self.assertFalse(candidate["price_available"])

    def test_market_filter_excludes_other_exchanges(self):
        other_stock = Stock.objects.create(
            symbol="OTHER",
            company_name="Other Company",
            exchange="NYSE",
            sector="Technology",
            industry="Software",
            is_active=True,
        )

        candidates = get_recommendation_candidates(
            market="NASDAQ",
            max_candidates=10,
        )

        symbols = {item["symbol"] for item in candidates}

        self.assertIn("TEST", symbols)
        self.assertNotIn(other_stock.symbol, symbols)

    def test_inactive_stock_is_excluded(self):
        self.stock.is_active = False
        self.stock.save(update_fields=["is_active"])

        candidates = get_recommendation_candidates(
            market="NASDAQ",
            max_candidates=10,
        )

        self.assertNotIn(
            "TEST",
            {item["symbol"] for item in candidates},
        )
