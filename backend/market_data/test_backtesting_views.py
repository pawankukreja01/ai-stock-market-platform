from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

import pandas as pd

from market_data.backtesting_views import build_backtest_execution_prices


class BacktestExecutionPriceQualityTests(SimpleTestCase):
    def test_invalid_ohlc_rows_remain_as_missing_execution_prices(self):
        frame = pd.DataFrame({
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "close_price": [100.0, 101.0, 102.0],
            "is_ohlc_valid": [True, False, True],
        })

        prices = build_backtest_execution_prices(frame)

        self.assertEqual(prices.iloc[0], 100.0)
        self.assertTrue(pd.isna(prices.iloc[1]))
        self.assertEqual(prices.iloc[2], 102.0)


class BacktestRequestValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_symbol_is_required(self):
        response = self.client.get("/api/backtest/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "symbol is required.")

    def test_unsupported_model_is_rejected(self):
        response = self.client.get("/api/backtest/", {"symbol": "AAPL", "model": "not-a-model"})
        self.assertEqual(response.status_code, 400)

    def test_unsupported_horizon_is_rejected(self):
        response = self.client.get("/api/backtest/", {"symbol": "AAPL", "horizon": "7"})
        self.assertEqual(response.status_code, 400)

    def test_non_finite_cost_or_threshold_is_rejected(self):
        for params in (
            {"transaction_cost_bps": "nan"},
            {"slippage_bps": "inf"},
            {"threshold": "-inf"},
        ):
            with self.subTest(params=params):
                query = {"symbol": "AAPL", **params}
                response = self.client.get("/api/backtest/", query)
                self.assertEqual(response.status_code, 400)
                self.assertIn("finite", response.data["error"])

    def test_negative_costs_are_rejected(self):
        response = self.client.get(
            "/api/backtest/",
            {"symbol": "AAPL", "transaction_cost_bps": "-1"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cannot be negative", response.data["error"])
