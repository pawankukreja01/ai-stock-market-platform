"""Paired market-feature ablation uses identical dates, folds and targets."""

from datetime import date
from io import StringIO
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from market_data.management.commands.compare_forecast_feature_sets import (
    evaluate_paired_feature_sets,
    prepare_paired_feature_sets,
)
from ml_models import create_zero_anchor_ridge_model


class PairedFeatureAlignmentTests(SimpleTestCase):
    def setUp(self):
        dates = pd.bdate_range("2022-01-03", periods=760)
        timeline = np.arange(len(dates), dtype=float)
        close = 100.0 * np.cumprod(
            1.0 + 0.0002 + 0.006 * np.sin(timeline / 13.0)
        )
        market = 4000.0 * np.cumprod(
            1.0 + 0.0001 + 0.004 * np.cos(timeline / 15.0)
        )
        self.frame = pd.DataFrame({
            "date": dates,
            "open_price": close * 0.999,
            "high_price": close * 1.01,
            "low_price": close * 0.99,
            "close_price": close,
            "volume": 1000000 + timeline * 10,
            "is_ohlc_valid": True,
            "is_volume_valid": True,
        })
        self.benchmark = pd.Series(market, index=dates, dtype=float)

    def test_aligns_identical_date_targets_and_folds(self):
        X_price, X_market, y = prepare_paired_feature_sets(
            self.frame, self.benchmark, horizon=5
        )
        self.assertTrue(X_price.index.equals(X_market.index))
        self.assertTrue(X_price.index.equals(y.index))
        self.assertIn("benchmark_return_1d", X_market.columns)
        self.assertNotIn("benchmark_return_1d", X_price.columns)
        self.assertGreaterEqual(len(y), 420)

        result = evaluate_paired_feature_sets(
            X_price, X_market, y,
            model_factory=create_zero_anchor_ridge_model,
            model_key="zero_anchor_ridge",
            horizon=5, min_train=300, test_size=60,
        )
        self.assertTrue(result["same_test_dates_and_targets"])
        self.assertGreaterEqual(result["folds"], 2)
        self.assertEqual(
            result["price_volume"]["out_of_sample_observations"],
            result["market_aligned"]["out_of_sample_observations"],
        )
        self.assertEqual(
            result["out_of_sample_observations"],
            result["price_volume"]["out_of_sample_observations"],
        )
        self.assertIsInstance(
            result["market_mae_improvement_percentage_points"], float
        )

    def test_sparse_benchmark_cannot_silently_fall_back(self):
        sparse = self.benchmark.copy()
        sparse.iloc[:240] = np.nan
        with self.assertRaisesRegex(ValueError, "benchmark features"):
            prepare_paired_feature_sets(self.frame, sparse, horizon=5)

    def test_target_mismatch_is_rejected(self):
        X_price, X_market, y = prepare_paired_feature_sets(
            self.frame, self.benchmark, horizon=5
        )
        corrupted = y.copy()
        corrupted.iloc[0] += 0.01
        with self.assertRaisesRegex(ValueError, "identical target dates"):
            evaluate_paired_feature_sets(
                X_price, X_market, corrupted.iloc[1:],
                model_factory=create_zero_anchor_ridge_model,
                model_key="zero_anchor_ridge",
                horizon=5, min_train=300, test_size=60,
            )

    def test_different_feature_dates_are_rejected(self):
        X_price, X_market, y = prepare_paired_feature_sets(
            self.frame, self.benchmark, horizon=5
        )
        with self.assertRaisesRegex(ValueError, "identical feature dates"):
            evaluate_paired_feature_sets(
                X_price.iloc[1:], X_market, y,
                model_factory=create_zero_anchor_ridge_model,
                model_key="zero_anchor_ridge",
                horizon=5, min_train=300, test_size=60,
            )


class PairedFeatureSafetyTests(SimpleTestCase):
    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_original_database_is_rejected_before_queries(self):
        with self.assertRaisesRegex(CommandError, "Refusing to run"):
            call_command(
                "compare_forecast_feature_sets",
                symbols=["ABF.L"],
                as_of="2026-06-30",
                stdout=StringIO(),
            )

    @patch.dict("os.environ", {"DB_NAME": ""})
    def test_missing_explicit_restored_database_is_rejected(self):
        with self.assertRaisesRegex(CommandError, "Refusing to run"):
            call_command(
                "compare_forecast_feature_sets",
                symbols=["AAPL"],
                as_of="2026-06-30",
                stdout=StringIO(),
            )
