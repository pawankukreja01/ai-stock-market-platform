"""Offline-only benchmark research contract: no provider calls or mutations."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase

from market_data.benchmark_data import (
    BenchmarkDataUnavailable,
    fetch_benchmark_prices,
    load_cached_benchmark_prices,
)
from market_data.management.commands.validate_stock_forecasts import (
    model_beats_all_baselines,
)


class OfflineMarketValidationTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cache_dir = Path(self.temp_dir.name)
        self.dates = pd.bdate_range("2024-01-02", periods=320)
        self.frame = pd.DataFrame({"date": self.dates})
        self.history = pd.DataFrame(
            {"Close": 3000.0 + pd.Series(range(len(self.dates))).to_numpy()},
            index=self.dates,
        )

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_complete_ftse_cache_is_read_without_network(self, ticker_factory):
        ticker_factory.return_value.history.return_value = self.history
        fetch_benchmark_prices(
            self.frame, "LSE", cache_dir=self.cache_dir, retry_delay_seconds=0
        )
        ticker_factory.reset_mock()
        ticker_factory.side_effect = AssertionError("Offline evaluation contacted Yahoo")
        result = load_cached_benchmark_prices(
            self.frame, "LSE", cache_dir=self.cache_dir
        )
        self.assertEqual(result.attrs["ticker"], "^FTSE")
        self.assertEqual(result.attrs["status"], "cache_hit")
        self.assertGreaterEqual(len(result), 300)
        ticker_factory.assert_not_called()

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_cache_miss_fails_closed_without_network(self, ticker_factory):
        with self.assertRaisesRegex(BenchmarkDataUnavailable, "cache missing"):
            load_cached_benchmark_prices(
                self.frame, "LSE", cache_dir=self.cache_dir
            )
        ticker_factory.assert_not_called()

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_wrong_market_does_not_substitute_us_cache(self, ticker_factory):
        ticker_factory.return_value.history.return_value = self.history
        fetch_benchmark_prices(
            self.frame, "NASDAQ", cache_dir=self.cache_dir, retry_delay_seconds=0
        )
        ticker_factory.reset_mock()
        with self.assertRaises(BenchmarkDataUnavailable):
            load_cached_benchmark_prices(
                self.frame, "LSE", cache_dir=self.cache_dir
            )
        ticker_factory.assert_not_called()

    def test_unsupported_market_is_rejected(self):
        with self.assertRaisesRegex(BenchmarkDataUnavailable, "No cached benchmark"):
            load_cached_benchmark_prices(
                self.frame, "UNKNOWN", cache_dir=self.cache_dir
            )
