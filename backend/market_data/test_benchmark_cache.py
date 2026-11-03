import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
from django.test import SimpleTestCase

from market_data.benchmark_data import (
    BenchmarkDataUnavailable,
    fetch_benchmark_prices,
)


class PersistentBenchmarkCacheTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.cache_dir = Path(self.temp_dir.name)
        self.dates = pd.bdate_range("2024-01-02", periods=8)
        self.prices = pd.DataFrame({"date": [self.dates[0], self.dates[-1]]})
        self.history = pd.DataFrame(
            {"Close": [100.0 + i for i in range(len(self.dates))]},
            index=self.dates,
        )

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_successful_download_is_cached_and_reused(self, ticker_factory):
        ticker_factory.return_value.history.return_value = self.history
        first = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir, retry_delay_seconds=0,
        )
        self.assertEqual(first.attrs["status"], "downloaded_and_cached")
        self.assertTrue(list(self.cache_dir.glob("*.csv")))
        self.assertTrue(list(self.cache_dir.glob("*.json")))

        second = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir, retry_delay_seconds=0,
        )
        self.assertEqual(second.attrs["status"], "cache_hit")
        self.assertTrue(second.attrs["cache_hit"])
        self.assertEqual(ticker_factory.call_count, 1)
        pd.testing.assert_series_equal(first, second, check_names=False)

    @patch("market_data.benchmark_data.time.sleep")
    @patch("market_data.benchmark_data.yf.Ticker")
    def test_strict_mode_retries_then_raises_on_uncached_range(self, ticker_factory, sleep_mock):
        ticker_factory.return_value.history.side_effect = RuntimeError("temporary provider failure")
        with self.assertRaises(BenchmarkDataUnavailable):
            fetch_benchmark_prices(
                self.prices, "NASDAQ", strict=True, cache_dir=self.cache_dir,
                download_attempts=3, retry_delay_seconds=0.1,
            )
        self.assertEqual(ticker_factory.return_value.history.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_non_strict_mode_keeps_optional_feature_fallback(self, ticker_factory):
        ticker_factory.return_value.history.side_effect = RuntimeError("offline")
        with patch("market_data.benchmark_data.time.sleep"):
            result = fetch_benchmark_prices(
                self.prices, "NASDAQ", cache_dir=self.cache_dir,
                download_attempts=1, retry_delay_seconds=0,
            )
        self.assertTrue(result.empty)
        self.assertEqual(result.attrs["status"], "download_failed")
        self.assertIn("cache miss", result.attrs["reason"].lower())

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_complete_cache_hit_needs_no_network(self, ticker_factory):
        ticker_factory.return_value.history.return_value = self.history
        fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir, retry_delay_seconds=0,
        )
        ticker_factory.reset_mock()
        ticker_factory.side_effect = AssertionError("network must not be called on cache hit")
        result = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir, retry_delay_seconds=0,
        )
        self.assertEqual(result.attrs["status"], "cache_hit")
        ticker_factory.assert_not_called()

    def test_invalid_retry_count_is_rejected(self):
        with self.assertRaises(ValueError):
            fetch_benchmark_prices(
                self.prices, "NASDAQ", cache_dir=self.cache_dir,
                download_attempts=0,
            )

    @patch("market_data.benchmark_data.time.sleep")
    @patch("market_data.benchmark_data.yf.Ticker")
    def test_rate_limit_stops_after_first_request_and_preserves_cache(
        self, ticker_factory, sleep_mock,
    ):
        ticker_factory.return_value.history.side_effect = RuntimeError(
            "HTTP 429 Too Many Requests"
        )
        result = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir,
            download_attempts=5, retry_delay_seconds=0.1,
        )
        self.assertTrue(result.empty)
        self.assertEqual(result.attrs["status"], "provider_rate_limited")
        self.assertEqual(ticker_factory.return_value.history.call_count, 1)
        sleep_mock.assert_not_called()
        self.assertFalse(list(self.cache_dir.glob("*.csv")))
        self.assertFalse(list(self.cache_dir.glob("*.json")))

    @patch("market_data.benchmark_data.time.sleep")
    @patch("market_data.benchmark_data.yf.Ticker")
    def test_strict_benchmark_mode_raises_immediately_after_429(
        self, ticker_factory, sleep_mock,
    ):
        ticker_factory.return_value.history.side_effect = RuntimeError(
            "HTTP 429 Too Many Requests"
        )
        with self.assertRaisesRegex(BenchmarkDataUnavailable, "rate limited"):
            fetch_benchmark_prices(
                self.prices, "NASDAQ", strict=True, cache_dir=self.cache_dir,
                download_attempts=5, retry_delay_seconds=0.1,
            )
        self.assertEqual(ticker_factory.return_value.history.call_count, 1)
        sleep_mock.assert_not_called()

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_complete_cache_is_returned_during_provider_outage(
        self, ticker_factory,
    ):
        ticker_factory.return_value.history.return_value = self.history
        initial = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir,
            retry_delay_seconds=0,
        )
        ticker_factory.reset_mock()
        ticker_factory.side_effect = AssertionError(
            "Cached data must not trigger a fresh Yahoo request."
        )
        offline = fetch_benchmark_prices(
            self.prices, "NASDAQ", cache_dir=self.cache_dir,
            download_attempts=5, retry_delay_seconds=0,
        )
        self.assertEqual(offline.attrs["status"], "cache_hit")
        self.assertEqual(offline.tolist(), initial.tolist())
        ticker_factory.assert_not_called()
