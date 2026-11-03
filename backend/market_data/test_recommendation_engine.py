from django.test import SimpleTestCase

from .recommendation_engine import (
    RISK_TOLERANCE_WEIGHTS,
    rank_feature_records,
    horizon_adjusted_weights,
)


def make_record(
    symbol,
    *,
    momentum,
    roe,
    volatility,
    drawdown,
    sharpe,
    sentiment,
    price_age=1,
    observations=100,
    eligible=True,
):
    return {
        "symbol": symbol,
        "company_name": symbol + " Company",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Software",
        "latest_price": 100.0,
        "latest_price_date": "2026-10-20",
        "price_age_days": price_age,
        "technical": {
            "return_20d": momentum,
            "sma20_ratio": (
                None if momentum is None
                else 1.02 if momentum > 0 else 0.98
            ),
            "sma50_ratio": (
                None if momentum is None
                else 1.01 if momentum > 0 else 0.99
            ),
        },
        "fundamentals": {
            "roe": roe,
            "profit_margin": 0.15 if roe is not None else None,
            "operating_margin": None,
            "current_ratio": None,
            "debt_to_equity": None,
            "pe_ratio": None,
        },
        "risk": {
            "risk_observations": observations,
            "annualised_volatility": volatility,
            "maximum_drawdown": drawdown,
            "sharpe_ratio": sharpe,
            "sortino_ratio": None,
        },
        "sentiment": {
            "sentiment_score": sentiment,
            "sentiment_articles": 5 if sentiment is not None else 0,
        },
        "data_quality": {
            "eligible_for_scoring": eligible,
            "exclusion_reasons": [],
        },
    }


class RecommendationEngineTests(SimpleTestCase):
    def setUp(self):
        self.records = [
            make_record(
                "AAA", momentum=0.12, roe=0.20,
                volatility=0.20, drawdown=-0.10,
                sharpe=1.1, sentiment=0.5,
            ),
            make_record(
                "BBB", momentum=-0.05, roe=0.05,
                volatility=0.45, drawdown=-0.30,
                sharpe=0.1, sentiment=-0.3,
            ),
            make_record(
                "CCC", momentum=0.06, roe=0.12,
                volatility=0.30, drawdown=-0.18,
                sharpe=0.6, sentiment=None,
            ),
        ]

    def test_returns_ranked_stocks_with_scores(self):
        result = rank_feature_records(self.records)

        self.assertEqual(result["scored_candidate_count"], 3)
        scores = [item["score"] for item in result["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0 <= score <= 100 for score in scores))

    def test_forecast_is_not_fabricated(self):
        result = rank_feature_records(self.records)

        self.assertFalse(result["forecast_included"])
        for item in result["results"]:
            self.assertIsNone(item["components"]["forecast"])

    def test_ineligible_stock_is_excluded(self):
        records = self.records + [
            make_record(
                "ZZZ", momentum=0.5, roe=0.5,
                volatility=0.1, drawdown=-0.05,
                sharpe=2.0, sentiment=0.9,
                eligible=False,
            )
        ]

        result = rank_feature_records(records)
        symbols = {item["symbol"] for item in result["results"]}

        self.assertNotIn("ZZZ", symbols)
        self.assertEqual(result["candidate_universe_size"], 4)
        self.assertEqual(result["eligible_candidate_count"], 3)

    def test_result_limit_does_not_change_input_universe(self):
        result = rank_feature_records(
            self.records, max_candidates=1
        )

        self.assertEqual(result["candidate_universe_size"], 3)
        self.assertEqual(result["scored_candidate_count"], 3)
        self.assertEqual(len(result["results"]), 1)

    def test_risk_tolerance_weights_are_distinct(self):
        self.assertNotEqual(
            RISK_TOLERANCE_WEIGHTS["low"],
            RISK_TOLERANCE_WEIGHTS["moderate"],
        )
        self.assertNotEqual(
            RISK_TOLERANCE_WEIGHTS["moderate"],
            RISK_TOLERANCE_WEIGHTS["high"],
        )

    def test_invalid_risk_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_feature_records(
                self.records, risk_tolerance="unknown"
            )

    def test_missing_metrics_remain_unscored(self):
        records = [
            make_record(
                "ONLY", momentum=None, roe=None,
                volatility=None, drawdown=None,
                sharpe=None, sentiment=None,
            )
        ]

        result = rank_feature_records(records)

        self.assertEqual(result["scored_candidate_count"], 0)
        self.assertEqual(result["results"], [])


    def test_risk_tolerance_changes_scores(self):
        low_risk = rank_feature_records(
            self.records,
            risk_tolerance="low",
        )
        high_risk = rank_feature_records(
            self.records,
            risk_tolerance="high",
        )

        low_scores = {
            item["symbol"]: item["score"]
            for item in low_risk["results"]
        }
        high_scores = {
            item["symbol"]: item["score"]
            for item in high_risk["results"]
        }

        self.assertNotEqual(low_scores, high_scores)

    def test_horizon_weights_are_transparent_and_preserve_total(self):
        short = horizon_adjusted_weights("moderate", 3)
        medium = horizon_adjusted_weights("moderate", 12)
        long_term = horizon_adjusted_weights("moderate", 60)

        self.assertGreater(short["momentum"], medium["momentum"])
        self.assertGreater(long_term["fundamentals"], medium["fundamentals"])
        self.assertLess(long_term["momentum"], medium["momentum"])
        for item in (short, medium, long_term):
            self.assertAlmostEqual(sum(item.values()), 1.0, places=6)
            self.assertTrue(all(0 <= weight <= 1 for weight in item.values()))

    def test_horizon_does_change_research_scores_without_fabricating_forecasts(self):
        short = rank_feature_records(self.records, horizon_months=3)
        long_term = rank_feature_records(self.records, horizon_months=60)
        self.assertNotEqual(short["scoring_weights"], long_term["scoring_weights"])
        self.assertEqual(short["horizon_months"], 3)
        self.assertEqual(long_term["horizon_months"], 60)
        self.assertFalse(short["forecast_included"])
        self.assertFalse(long_term["forecast_included"])

    def test_unsupported_horizon_cannot_be_scored(self):
        for value in (0, 601, True, 3.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    horizon_adjusted_weights("moderate", value)
