from django.test import SimpleTestCase
import pandas as pd

from backtesting import (
    backtest_long_flat_strategy,
    prepare_horizon_backtest_window,
)


class HorizonMatchedBacktestTests(SimpleTestCase):
    def test_signal_controls_exact_non_overlapping_horizon_blocks(self):
        index = pd.date_range("2024-01-01", periods=10, freq="B")
        prices = pd.Series([100.0 + i for i in range(10)], index=index)
        signals = pd.Series([1, 0, 0, 0, 0, 0, 1, 0, 0, 0], index=index, dtype=float)

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=0,
            slippage_bps=0,
            holding_period=3,
        )

        # Row 0 has no daily return. Forecasts at rows 0, 3 and 6 govern
        # the next three close-to-close returns each.
        self.assertEqual(
            result["daily"]["position"].astype(int).tolist(),
            [1, 1, 1, 0, 0, 0, 1, 1, 1],
        )

    def test_one_day_horizon_preserves_one_day_signal_shift(self):
        index = pd.date_range("2024-02-01", periods=5, freq="B")
        prices = pd.Series([100.0, 101.0, 100.0, 102.0, 101.0], index=index)
        signals = pd.Series([1, 0, 1, 0, 1], index=index, dtype=float)

        result = backtest_long_flat_strategy(
            prices, signals, transaction_cost_bps=0, slippage_bps=0, holding_period=1
        )
        self.assertEqual(result["daily"]["position"].astype(int).tolist(), [1, 0, 1, 0])

    def test_backtest_window_includes_full_final_selected_holding_block(self):
        index = pd.date_range("2024-03-01", periods=30, freq="B")
        prices = pd.Series([100.0 + i for i in range(30)], index=index)
        predictions = pd.Series([0.01] * 12, index=index[5:17])

        window_prices, window_predictions = prepare_horizon_backtest_window(
            prices, predictions, holding_period=5
        )

        # Selected forecasts are at offsets 0, 5 and 10 from the first OOS
        # date. The final one needs five following price-return observations.
        self.assertEqual(window_prices.index[0], index[5])
        self.assertEqual(window_prices.index[-1], index[20])
        self.assertEqual(len(window_prices), 16)
        self.assertTrue(pd.notna(window_predictions.loc[index[15]]))
        self.assertTrue(window_predictions.loc[index[17:20]].isna().all())

    def test_holding_period_must_be_positive_integer(self):
        index = pd.date_range("2024-04-01", periods=3, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0], index=index)
        signals = pd.Series([1.0, 1.0, 1.0], index=index)
        with self.assertRaises(ValueError):
            backtest_long_flat_strategy(prices, signals, holding_period=0)
