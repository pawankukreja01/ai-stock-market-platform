"""Regression coverage for market-aware UK/US risk and benchmark displays."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
from django.test import TestCase
from rest_framework.test import APIClient

from market_data.models import HistoricalPrice
from stocks.models import Stock


class MarketAwareRiskAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.us = Stock.objects.create(
            symbol="AAPL", company_name="Apple", exchange="NASDAQ",
            is_active=True,
        )
        self.uk = Stock.objects.create(
            symbol="ABF.L", company_name="AB Foods", exchange="LSE",
            is_active=True,
        )
        for stock in (self.us, self.uk):
            for index in range(6):
                value = Decimal("100.00") + Decimal(index)
                HistoricalPrice.objects.create(
                    stock=stock,
                    date=date(2026, 10, 20) + timedelta(days=index),
                    open_price=value,
                    high_price=value + 1,
                    low_price=value - 1,
                    close_price=value,
                    adjusted_close=value,
                    volume=1000,
                )

    @patch("market_data.views.fetch_cached_benchmark_prices")
    def test_london_stock_uses_ftse_for_beta_and_correlation(self, fetch):
        index = pd.date_range("2026-10-20", periods=6)
        series = pd.Series([100, 101, 102, 103, 104, 105], index=index)
        series.attrs["status"] = "cache_hit"
        fetch.return_value = series

        response = self.client.get("/api/risk-metrics/", {"symbol": "ABF.L"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["benchmark"], "^FTSE")
        self.assertEqual(response.data["risk_metrics"]["benchmark"], "^FTSE")
        self.assertEqual(response.data["benchmark_status"], "cache_hit")
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.kwargs["exchange"], "LSE")

    @patch("market_data.views.fetch_cached_benchmark_prices")
    def test_us_stock_uses_sp500(self, fetch):
        fetch.return_value = pd.Series(dtype=float)
        response = self.client.get("/api/risk-metrics/", {"symbol": "AAPL"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["benchmark"], "^GSPC")
        self.assertIsNone(response.data["risk_metrics"]["beta"])
        self.assertIsNone(response.data["risk_metrics"]["benchmark_correlation"])

    @patch("market_data.views.fetch_cached_benchmark_prices")
    def test_unavailable_ftse_is_not_replaced_by_us_index(self, fetch):
        fetch.side_effect = RuntimeError("Yahoo Finance unavailable")
        response = self.client.get("/api/risk-metrics/", {"symbol": "ABF.L"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["benchmark"], "^FTSE")
        self.assertEqual(response.data["benchmark_status"], "unavailable")
        self.assertIsNone(response.data["risk_metrics"]["beta"])
        self.assertIsNone(response.data["risk_metrics"]["benchmark_correlation"])


class MarketAwareBenchmarkComparisonTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("market_data.views.yf.Ticker")
    @patch("market_data.views.fetch_cached_benchmark_prices")
    def test_london_comparison_uses_cached_ftse_not_us_indexes(self, fetch, ticker):
        fetch.return_value = pd.Series(
            [100, 102, 103],
            index=pd.date_range("2026-10-19", periods=3),
            dtype=float,
        )

        response = self.client.get("/api/benchmark-comparison/", {
            "exchange": "LSE",
            "start_date": "2026-10-19",
            "end_date": "2026-10-25",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["market"], "UK")
        self.assertEqual(response.data["benchmarks"]["sp500"]["name"], "FTSE 100")
        self.assertEqual(response.data["benchmarks"]["sp500"]["symbol"], "^FTSE")
        self.assertEqual(len(response.data["benchmarks"]["sp500"]["dates"]), 3)
        self.assertEqual(response.data["benchmarks"]["nasdaq100"]["dates"], [])
        self.assertEqual(response.data["benchmarks"]["sector"]["dates"], [])
        fetch.assert_called_once()
        ticker.assert_not_called()

    @patch("market_data.views.yf.Ticker")
    def test_us_comparison_keeps_sp500_and_nasdaq(self, ticker):
        history = pd.DataFrame(
            {"Close": [100, 101]},
            index=pd.date_range("2026-10-19", periods=2),
        )
        ticker.return_value.history.return_value = history
        response = self.client.get("/api/benchmark-comparison/", {
            "exchange": "NASDAQ",
            "start_date": "2026-10-19",
            "end_date": "2026-10-25",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["market"], "US")
        self.assertEqual(response.data["benchmarks"]["sp500"]["symbol"], "^GSPC")
        self.assertEqual(response.data["benchmarks"]["nasdaq100"]["symbol"], "^NDX")
        self.assertEqual(ticker.call_count, 3)
