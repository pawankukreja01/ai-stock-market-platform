import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from backtesting import (
    backtest_long_flat_strategy,
    prepare_horizon_backtest_window,
)


class BacktestingPriceIntegrityTests(SimpleTestCase):
    def test_execution_rejects_missing_price_instead_of_bridging(self):
        index = pd.RangeIndex(5)
        prices = pd.Series([100.0, 101.0, np.nan, 104.0, 105.0], index=index)
        signal = pd.Series([1.0] * len(index), index=index)
        with self.assertRaisesRegex(ValueError, "cannot be dropped or bridged"):
            backtest_long_flat_strategy(prices, signal)

    def test_execution_rejects_non_positive_and_infinite_prices(self):
        signal = pd.Series([1.0, 1.0, 1.0], index=pd.RangeIndex(3))
        for bad_price in (0.0, -1.0, np.inf, -np.inf):
            with self.subTest(bad_price=bad_price):
                prices = pd.Series([100.0, bad_price, 102.0], index=pd.RangeIndex(3))
                with self.assertRaisesRegex(ValueError, "finite and positive"):
                    backtest_long_flat_strategy(prices, signal)

    def test_horizon_window_preserves_and_rejects_missing_price_date(self):
        index = pd.RangeIndex(10)
        prices = pd.Series([100.0 + i for i in range(10)], index=index)
        prices.iloc[3] = np.nan
        predictions = pd.Series([0.01, 0.02, 0.03, 0.04], index=[0, 2, 4, 6])
        with self.assertRaisesRegex(ValueError, "refusing to bridge"):
            prepare_horizon_backtest_window(prices, predictions, holding_period=2)

    def test_horizon_window_accepts_positive_prices_and_keeps_full_final_block(self):
        index = pd.RangeIndex(10)
        prices = pd.Series([100.0 + i for i in range(10)], index=index)
        predictions = pd.Series([0.01, 0.02, 0.03, 0.04], index=[0, 2, 4, 6])
        window_prices, window_predictions = prepare_horizon_backtest_window(
            prices, predictions, holding_period=2
        )
        self.assertEqual(window_prices.index[0], 0)
        self.assertEqual(window_prices.index[-1], 7)
        self.assertEqual(window_predictions.loc[6], 0.04)
