import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from .risk_engine import calculate_daily_returns, calculate_risk_metrics


class RiskEngineMissingPriceTests(SimpleTestCase):
    def test_missing_close_does_not_create_a_multi_session_daily_return(self):
        dates = pd.bdate_range("2026-01-05", periods=4)
        prices = pd.Series([100.0, np.nan, 110.0, 111.0], index=dates)

        returns = calculate_daily_returns(prices)

        self.assertEqual(len(returns), 1)
        self.assertEqual(returns.index[-1], dates[-1])
        self.assertAlmostEqual(float(returns.iloc[-1]), (111.0 / 110.0) - 1.0)

    def test_non_positive_close_preserves_a_gap(self):
        dates = pd.bdate_range("2026-01-05", periods=4)
        prices = pd.Series([100.0, 0.0, 110.0, 111.0], index=dates)

        returns = calculate_daily_returns(prices)

        self.assertEqual(len(returns), 1)
        self.assertAlmostEqual(float(returns.iloc[-1]), (111.0 / 110.0) - 1.0)

    def test_risk_metrics_report_valid_close_and_return_counts_separately(self):
        dates = pd.bdate_range("2026-01-05", periods=4)
        prices = pd.Series([100.0, np.nan, 110.0, 111.0], index=dates)

        metrics = calculate_risk_metrics(prices)

        self.assertEqual(metrics["observations"], 3)
        self.assertEqual(metrics["return_observations"], 1)
