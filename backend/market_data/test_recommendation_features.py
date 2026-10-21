from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from stocks.models import Stock
from market_data.models import HistoricalPrice
from market_data.recommendation_features import (
    extract_candidate_features,
)


class RecommendationFeatureTests(TestCase):
    def setUp(self):
        self.stock = Stock.objects.create(
            symbol="FEAT",
            company_name="Feature Test Company",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )

    def add_prices(self, count=100):
        today = date.today()

        for index in range(count):
            # Deterministic, positive prices with a small upward trend.
            close = Decimal("100.00") + Decimal(index) / Decimal("10")
            price_date = today - timedelta(days=count - index - 1)

            HistoricalPrice.objects.create(
                stock=self.stock,
                date=price_date,
                open_price=close,
                high_price=close + Decimal("1.00"),
                low_price=close - Decimal("1.00"),
                close_price=close,
                adjusted_close=close,
                volume=1000,
            )

    def test_missing_data_is_not_fabricated(self):
        result = extract_candidate_features(
            self.stock,
            as_of=date.today(),
        )

        self.assertIsNone(result["latest_price"])
        self.assertFalse(
            result["data_quality"]["eligible_for_scoring"]
        )
        self.assertTrue(
            result["data_quality"]["exclusion_reasons"]
        )

    def test_sufficient_recent_prices_enable_risk_assessment(self):
        self.add_prices(count=100)

        result = extract_candidate_features(
            self.stock,
            as_of=date.today(),
        )

        self.assertIsNotNone(result["latest_price"])
        self.assertTrue(result["risk"]["risk_data_available"])
        self.assertEqual(result["risk"]["risk_observations"], 100)
        self.assertTrue(
            result["data_quality"]["eligible_for_scoring"]
        )

    def test_insufficient_history_does_not_enable_risk_assessment(self):
        self.add_prices(count=30)

        result = extract_candidate_features(
            self.stock,
            as_of=date.today(),
        )

        self.assertFalse(result["risk"]["risk_data_available"])
        self.assertFalse(
            result["data_quality"]["eligible_for_scoring"]
        )

    def test_stale_prices_are_excluded(self):
        self.add_prices(count=100)

        # Evaluate the same data from a date eight days later.
        result = extract_candidate_features(
            self.stock,
            as_of=date.today() + timedelta(days=8),
        )

        self.assertFalse(
            result["data_quality"]["eligible_for_scoring"]
        )
        self.assertTrue(
            any(
                "more than seven days old" in reason
                for reason in result["data_quality"]["exclusion_reasons"]
            )
        )
