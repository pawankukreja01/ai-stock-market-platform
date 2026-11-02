from unittest.mock import patch

import pandas as pd
from django.test import SimpleTestCase

from market_data.benchmark_data import BENCHMARK_TICKERS, fetch_benchmark_prices
from stocks.catalog import MARKET_EXCHANGES


def exchange_for_market(wanted_market):
    for market, exchanges in MARKET_EXCHANGES.items():
        if str(market).strip().upper() == wanted_market:
            return next(iter(exchanges))
    raise AssertionError(f"No exchange mapping found for market {wanted_market!r}")


class BenchmarkDataTests(SimpleTestCase):
    def setUp(self):
        self.price_df = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
        })
        self.history = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.DatetimeIndex(["2024-01-02", "2024-01-03"], tz="UTC"),
        )

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_us_exchange_uses_sp500_benchmark(self, ticker_class):
        ticker_class.return_value.history.return_value = self.history
        result = fetch_benchmark_prices(self.price_df, exchange=exchange_for_market("US"))

        ticker_class.assert_called_once_with(BENCHMARK_TICKERS["US"])
        ticker_class.return_value.history.assert_called_once_with(
            start="2024-01-02",
            end="2024-01-05",
            auto_adjust=False,
            actions=False,
        )
        self.assertEqual(result.tolist(), [100.0, 101.0])

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_uk_exchange_uses_ftse100_benchmark(self, ticker_class):
        ticker_class.return_value.history.return_value = self.history
        result = fetch_benchmark_prices(self.price_df, exchange=exchange_for_market("UK"))

        ticker_class.assert_called_once_with(BENCHMARK_TICKERS["UK"])
        self.assertEqual(result.tolist(), [100.0, 101.0])

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_unsupported_exchange_returns_empty_series_without_download(self, ticker_class):
        result = fetch_benchmark_prices(self.price_df, exchange="UNKNOWN_EXCHANGE")

        self.assertTrue(result.empty)
        ticker_class.assert_not_called()

    @patch("market_data.benchmark_data.yf.Ticker")
    def test_download_failure_returns_empty_series(self, ticker_class):
        ticker_class.return_value.history.side_effect = RuntimeError("feed unavailable")
        result = fetch_benchmark_prices(self.price_df, exchange=exchange_for_market("US"))

        self.assertTrue(result.empty)

    def test_empty_price_history_returns_empty_series(self):
        result = fetch_benchmark_prices(pd.DataFrame(columns=["date"]), exchange="NASDAQ")
        self.assertTrue(result.empty)

# _isolate_benchmark_cache_for_each_legacy_test: use a fresh temporary cache for each legacy benchmark-data test.
import tempfile as _benchmark_test_tempfile
import time as _benchmark_test_time
from functools import wraps as _benchmark_test_wraps
from pathlib import Path as _benchmark_test_Path
from unittest import mock as _benchmark_test_mock

def _isolate_benchmark_cache_for_each_legacy_test(test_method):
    @_benchmark_test_wraps(test_method)
    def _wrapped(self, *args, **kwargs):
        with _benchmark_test_tempfile.TemporaryDirectory() as _cache_directory:
            with _benchmark_test_mock.patch(
                "market_data.benchmark_data.DEFAULT_CACHE_DIR",
                _benchmark_test_Path(_cache_directory),
            ):
                return test_method(self, *args, **kwargs)
    return _wrapped

for _benchmark_test_name in dir(BenchmarkDataTests):
    if _benchmark_test_name.startswith("test_"):
        _benchmark_test_method = getattr(BenchmarkDataTests, _benchmark_test_name)
        setattr(
            BenchmarkDataTests,
            _benchmark_test_name,
            _isolate_benchmark_cache_for_each_legacy_test(_benchmark_test_method),
        )
