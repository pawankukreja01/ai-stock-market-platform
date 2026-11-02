"""Regression tests for leakage-safe market-relative return features."""
import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml_engine import build_stock_features


class RelativeReturnFeatureTests(SimpleTestCase):
    def setUp(self):
        self.dates = pd.date_range("2023-01-02", periods=320, freq="B")
        steps = np.arange(len(self.dates), dtype=float)
        stock_daily_returns = 0.0003 + 0.008 * np.sin(steps / 8.0)
        market_daily_returns = 0.0002 + 0.005 * np.cos(steps / 10.0)
        self.close = pd.Series(
            100.0 * np.cumprod(1.0 + stock_daily_returns),
            index=self.dates,
        )
        self.benchmark_close = pd.Series(
            4000.0 * np.cumprod(1.0 + market_daily_returns),
            index=self.dates,
        )
        self.prices = pd.DataFrame({
            "date": self.dates,
            "high_price": self.close.to_numpy() * 1.01,
            "low_price": self.close.to_numpy() * 0.99,
            "close_price": self.close.to_numpy(),
            "volume": 1_000_000.0 + steps * 100.0,
        })

    def test_relative_returns_equal_stock_return_minus_benchmark_return(self):
        features = build_stock_features(
            self.prices,
            benchmark_prices=self.benchmark_close,
        )
        date = self.dates[-1]

        for period in (1, 5, 20, 60):
            column = f"relative_return_{period}d"
            self.assertIn(column, features.columns)
            expected = (
                self.close.pct_change(periods=period, fill_method=None).loc[date]
                - self.benchmark_close.pct_change(periods=period, fill_method=None).loc[date]
            )
            self.assertAlmostEqual(float(features.loc[date, column]), float(expected), places=10)

    def test_relative_return_features_are_absent_without_benchmark(self):
        features = build_stock_features(self.prices)
        self.assertFalse(any(column.startswith("relative_return_") for column in features.columns))

    def test_sparse_benchmark_does_not_add_benchmark_or_relative_features(self):
        sparse_benchmark = self.benchmark_close.copy()
        sparse_benchmark.iloc[:100] = np.nan

        features = build_stock_features(
            self.prices,
            benchmark_prices=sparse_benchmark,
        )
        self.assertFalse(any(column.startswith("relative_return_") for column in features.columns))
        self.assertNotIn("benchmark_return_1d", features.columns)
        self.assertNotIn("benchmark_return_20d", features.columns)
