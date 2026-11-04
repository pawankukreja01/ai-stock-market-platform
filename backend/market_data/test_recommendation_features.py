from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

from django.test import TestCase

from stocks.models import Stock
from market_data.models import HistoricalPrice, Fundamental, NewsArticle
from market_data.recommendation_features import (
    extract_candidate_features,
)
from market_data.recommendation_engine import recommend_stocks


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

    def test_future_period_fundamentals_are_not_used_in_current_rankings(self):
        self.add_prices(count=100)
        future = Fundamental.objects.create(
            stock=self.stock, period_type="annual",
            period_end=date.today() + timedelta(days=30),
            roe=Decimal("0.99"),
        )
        result = extract_candidate_features(self.stock, as_of=date.today())
        self.assertFalse(result["data_quality"]["fundamental_data_available"])
        self.assertIsNone(result["fundamentals"].get("roe"))
        future.period_end = date.today() - timedelta(days=30)
        future.save(update_fields=["period_end"])
        result_now = extract_candidate_features(self.stock, as_of=date.today())
        self.assertEqual(result_now["fundamentals"]["roe"], 0.99)

    def test_backfilled_fundamentals_are_not_used_before_they_were_ingested(self):
        self.add_prices(count=100)
        as_of = date.today() - timedelta(days=10)
        Fundamental.objects.create(
            stock=self.stock, period_type="annual",
            period_end=as_of - timedelta(days=30),
            roe=Decimal("0.8"),
        )
        result = extract_candidate_features(self.stock, as_of=as_of)
        self.assertFalse(result["data_quality"]["fundamental_data_available"])
        self.assertEqual(result["data_quality"]["evidence_cutoff_date"], as_of.isoformat())

    def test_revised_fundamentals_are_excluded_from_past_cutoffs(self):
        self.add_prices(count=100)
        statement = Fundamental.objects.create(
            stock=self.stock, period_type="annual",
            period_end=date.today() - timedelta(days=60),
            roe=Decimal("0.6"),
        )
        # An update made after the signal date cannot be retroactively
        # displayed in that historical ranking.
        Fundamental.objects.filter(pk=statement.pk).update(
            updated_at=timezone.now() + timedelta(days=1)
        )
        result = extract_candidate_features(self.stock, as_of=date.today())
        self.assertFalse(result["data_quality"]["fundamental_data_available"])

    def test_sentiment_rejects_future_analysis_and_post_cutoff_ingestion(self):
        self.add_prices(count=100)
        as_of = date.today()
        article = NewsArticle.objects.create(
            stock=self.stock,
            title="Archived earnings report",
            url="https://example.invalid/news-1",
            published_at=timezone.now() - timedelta(days=1),
            sentiment_score=0.7,
            sentiment_analyzed_at=timezone.now() + timedelta(days=1),
        )
        result = extract_candidate_features(self.stock, as_of=as_of)
        self.assertEqual(result["sentiment"]["sentiment_articles"], 0)

        article.sentiment_analyzed_at = timezone.now()
        article.save(update_fields=["sentiment_analyzed_at"])
        result_today = extract_candidate_features(self.stock, as_of=as_of)
        self.assertEqual(result_today["sentiment"]["sentiment_articles"], 1)

        yesterday = as_of - timedelta(days=1)
        result_before_ingestion = extract_candidate_features(self.stock, as_of=yesterday)
        self.assertEqual(result_before_ingestion["sentiment"]["sentiment_articles"], 0)

    def test_unknown_filing_date_is_not_assumed_available(self):
        self.add_prices(count=100)
        Fundamental.objects.create(
            stock=self.stock, period_type="quarterly",
            period_end=None, roe=Decimal("0.9"),
        )
        result = extract_candidate_features(self.stock, as_of=date.today())
        self.assertFalse(result["data_quality"]["fundamental_data_available"])

    def test_invalid_latest_close_uses_previous_positive_close(self):
        self.add_prices(count=100)
        latest = HistoricalPrice.objects.get(stock=self.stock, date=date.today())
        latest.close_price = Decimal("0")
        latest.adjusted_close = Decimal("0")
        latest.save(update_fields=["close_price", "adjusted_close"])

        result = extract_candidate_features(self.stock, as_of=date.today())

        expected = HistoricalPrice.objects.get(
            stock=self.stock, date=date.today() - timedelta(days=1)
        )
        self.assertEqual(result["latest_price"], float(expected.close_price))
        self.assertEqual(result["latest_price_date"], expected.date.isoformat())
        self.assertTrue(result["risk"]["risk_data_available"])

    def test_positive_close_remains_usable_when_ohlc_flag_is_invalid(self):
        self.add_prices(count=100)
        latest = HistoricalPrice.objects.get(stock=self.stock, date=date.today())
        latest.is_ohlc_valid = False
        latest.quality_flags = ["HIGH_BELOW_CLOSE"]
        latest.save(update_fields=["is_ohlc_valid", "quality_flags"])

        result = extract_candidate_features(self.stock, as_of=date.today())

        self.assertEqual(result["latest_price"], float(latest.close_price))
        self.assertTrue(result["data_quality"]["price_available"])
        self.assertTrue(result["risk"]["risk_data_available"])

    def test_recommendation_universe_excludes_future_only_stock(self):
        self.add_prices(count=100)
        future_stock = Stock.objects.create(
            symbol="FUTR",
            company_name="Future-only Price Company",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True,
        )
        future_close = Decimal("150.00")
        HistoricalPrice.objects.create(
            stock=future_stock,
            date=date.today() + timedelta(days=1),
            open_price=future_close,
            high_price=future_close,
            low_price=future_close,
            close_price=future_close,
            adjusted_close=future_close,
            volume=1000,
        )

        result = recommend_stocks(as_of=date.today())

        self.assertEqual(result["candidate_universe_size"], 1)

    def test_future_prices_are_excluded_by_as_of_date(self):
        self.add_prices(count=100)
        future_date = date.today() + timedelta(days=1)
        future_close = Decimal("999.00")
        HistoricalPrice.objects.create(
            stock=self.stock,
            date=future_date,
            open_price=future_close,
            high_price=future_close,
            low_price=future_close,
            close_price=future_close,
            adjusted_close=future_close,
            volume=1000,
        )

        result = extract_candidate_features(self.stock, as_of=date.today())

        self.assertEqual(result["latest_price"], 109.9)
        self.assertEqual(result["latest_price_date"], date.today().isoformat())
        self.assertEqual(result["risk"]["risk_observations"], 100)

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
