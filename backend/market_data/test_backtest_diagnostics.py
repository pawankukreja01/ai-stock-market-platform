import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from backtesting import backtest_long_flat_strategy


class BacktestTradeDiagnosticsTests(SimpleTestCase):
    def test_gross_net_cost_breakdown_and_holding_diagnostics(self):
        index = pd.date_range("2024-05-01", periods=4, freq="B")
        prices = pd.Series([100.0, 100.0, 110.0, 110.0], index=index)
        signals = pd.Series([1.0, np.nan, np.nan, np.nan], index=index)

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=10.0,
            slippage_bps=20.0,
            holding_period=2,
        )

        metrics = result["metrics"]
        trade = result["trades"][0]
        expected_net = (1 - 0.003) * 1.10 * (1 - 0.003) - 1

        self.assertAlmostEqual(metrics["gross_cumulative_return"], 0.10)
        self.assertAlmostEqual(metrics["net_cumulative_return"], expected_net)
        self.assertAlmostEqual(
            metrics["gross_to_net_return_drag"], 0.10 - expected_net
        )
        self.assertAlmostEqual(metrics["total_transaction_cost"], 0.002)
        self.assertAlmostEqual(metrics["total_slippage_cost"], 0.004)
        self.assertAlmostEqual(metrics["total_trading_cost"], 0.006)
        self.assertAlmostEqual(metrics["total_turnover"], 2.0)
        self.assertAlmostEqual(metrics["exposure_pct"], 2 / 3)

        self.assertEqual(metrics["completed_trades"], 1)
        self.assertEqual(metrics["average_holding_sessions"], 2.0)
        self.assertAlmostEqual(trade["gross_return"], 0.10)
        self.assertAlmostEqual(trade["net_return"], expected_net)
        self.assertAlmostEqual(trade["transaction_cost"], 0.002)
        self.assertAlmostEqual(trade["slippage_cost"], 0.004)
        self.assertAlmostEqual(trade["total_cost"], 0.006)
        self.assertEqual(trade["holding_sessions"], 2)
        self.assertEqual(trade["return"], trade["net_return"])

    def test_average_winning_and_losing_trade_returns_use_closed_net_trades(self):
        index = pd.date_range("2024-06-03", periods=9, freq="B")
        prices = pd.Series(
            [100.0, 100.0, 110.0, 110.0, 110.0, 110.0, 100.0, 100.0, 100.0],
            index=index,
        )
        signals = pd.Series(np.nan, index=index)
        signals.iloc[0] = 1.0
        signals.iloc[4] = 1.0

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
            holding_period=2,
        )

        metrics = result["metrics"]
        self.assertEqual(metrics["completed_trades"], 2)
        self.assertAlmostEqual(metrics["win_rate"], 0.5)
        self.assertAlmostEqual(metrics["average_winning_trade_return"], 0.10)
        self.assertAlmostEqual(
            metrics["average_losing_trade_return"], (100.0 / 110.0) - 1.0
        )
        self.assertAlmostEqual(metrics["profit_factor"], 1.1)
        self.assertEqual(
            [trade["holding_sessions"] for trade in result["trades"]],
            [2, 2],
        )

    def test_buy_and_hold_win_rate_is_one_completed_position_not_daily_accuracy(self):
        index = pd.date_range("2024-07-01", periods=6, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0], index=index)
        signals = pd.Series(1.0, index=index)

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=0.0,
            slippage_bps=0.0,
            non_overlapping_horizon=False,
        )

        self.assertEqual(result["metrics"]["completed_trades"], 1)
        self.assertEqual(result["metrics"]["win_rate"], 1.0)
        self.assertEqual(len(result["trades"]), 1)
        self.assertGreater(result["trades"][0]["holding_sessions"], 1)

    def test_no_completed_trades_has_zero_exposure_and_empty_ledger(self):
        index = pd.date_range("2024-08-01", periods=5, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=index)
        signals = pd.Series(0.0, index=index)

        result = backtest_long_flat_strategy(prices, signals)

        self.assertEqual(result["trades"], [])
        self.assertEqual(result["metrics"]["completed_trades"], 0)
        self.assertEqual(result["metrics"]["exposure_pct"], 0.0)
        self.assertIsNone(result["metrics"]["average_holding_sessions"])
        self.assertIsNone(result["metrics"]["average_winning_trade_return"])
        self.assertIsNone(result["metrics"]["average_losing_trade_return"])

class BacktestSensitivityDiagnosticsTests(SimpleTestCase):
    def test_sensitivity_scenarios_expose_gross_and_separate_cost_metrics(self):
        from backtest_sensitivity import run_cost_slippage_sensitivity

        index = pd.date_range("2023-01-02", periods=260, freq="B")
        prices = pd.Series(100.0 + np.arange(260, dtype=float) * 0.1, index=index)
        predictions = pd.Series([0.01, 0.01], index=index[[220, 222]])

        result = run_cost_slippage_sensitivity(
            prices,
            predictions,
            selected_transaction_cost_bps=5.0,
            selected_slippage_bps=5.0,
            holding_period=1,
            cost_levels_bps=[0.0, 10.0],
            slippage_levels_bps=[0.0, 20.0],
        )

        selected = next(
            row for row in result["scenarios"]
            if row["is_selected_configuration"]
        )
        metrics = selected["strategies"]["ml"]
        self.assertIn("gross_cumulative_return", metrics)
        self.assertIn("gross_to_net_return_drag", metrics)
        self.assertIn("total_transaction_cost", metrics)
        self.assertIn("total_slippage_cost", metrics)
        self.assertIn("total_turnover", metrics)
