import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from backtesting import (
    backtest_long_flat_strategy,
    calculate_maximum_drawdown,
    compare_strategies,
    extract_trades,
    prepare_horizon_backtest_window,
    choose_walk_forward_test_size,
    choose_walk_forward_step_size,
)
from walk_forward import generate_walk_forward_splits


class ExecutableHorizonBacktestTests(SimpleTestCase):
    def test_forecast_enters_next_close_and_holds_h_return_sessions(self):
        index = pd.date_range("2024-01-01", periods=10, freq="B")
        prices = pd.Series([100.0 + i for i in range(10)], index=index)
        signals = pd.Series(0.0, index=index)
        signals.iloc[0] = 1.0
        signals.iloc[4] = 1.0

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=0,
            slippage_bps=0,
            holding_period=3,
        )

        # Signal 0 executes at close 1; return exposure starts on row 2 and
        # continues through row 4 (three return intervals). Signal 4 executes
        # at close 5 and earns rows 6, 7 and 8.
        self.assertEqual(
            result["daily"]["position"].astype(int).tolist(),
            [0, 1, 1, 1, 0, 1, 1, 1, 0],
        )
        self.assertEqual(
            result["daily"]["execution_position"].astype(int).tolist(),
            [1, 1, 1, 0, 1, 1, 1, 0, 0],
        )

    def test_horizon_window_samples_next_available_forecast_after_prior_exit(self):
        index = pd.date_range("2024-03-01", periods=40, freq="B")
        prices = pd.Series([100.0 + i for i in range(40)], index=index)
        # Sparse forecast points emulate OOS test folds separated by purge gaps.
        predictions = pd.Series(
            [0.01, 0.02, 0.03, 0.04],
            index=[index[5], index[11], index[23], index[29]],
        )

        window_prices, window_predictions = prepare_horizon_backtest_window(
            prices, predictions, holding_period=5
        )

        # Forecasts at 5, 11, 23 and 29: 5 and 11 are non-overlapping
        # (the next decision may occur on the prior exit date); 23 and 29
        # form the next executable pair after the sparse gap.
        self.assertEqual(window_prices.index[0], index[5])
        self.assertEqual(window_prices.index[-1], index[35])
        self.assertEqual(window_predictions.loc[index[5]], 0.01)
        self.assertEqual(window_predictions.loc[index[11]], 0.02)
        self.assertEqual(window_predictions.loc[index[23]], 0.03)
        self.assertEqual(window_predictions.loc[index[29]], 0.04)

    def test_backtest_window_requires_two_complete_executable_forecasts(self):
        index = pd.date_range("2024-02-01", periods=8, freq="B")
        prices = pd.Series([100.0 + i for i in range(8)], index=index)
        predictions = pd.Series([0.01, 0.02], index=[index[0], index[2]])
        with self.assertRaisesRegex(ValueError, "At least two executable"):
            prepare_horizon_backtest_window(prices, predictions, holding_period=5)

    def test_sma_comparator_uses_pre_test_history_for_warmup(self):
        index = pd.date_range("2023-01-01", periods=260, freq="B")
        prices = pd.Series(100.0 + pd.Series(range(260), index=index) * 0.1, index=index)
        predictions = pd.Series([0.01, 0.01], index=index[[220, 222]])
        # Two forecasts must have complete H+1 exit price paths.
        compare_strategies(
            prices,
            predictions,
            transaction_cost_bps=0,
            slippage_bps=0,
            sma_period=200,
            holding_period=1,
        )

    def test_holding_period_must_be_positive_integer(self):
        index = pd.date_range("2024-04-01", periods=5, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=index)
        signals = pd.Series([1.0] * len(index), index=index)
        with self.assertRaises(ValueError):
            backtest_long_flat_strategy(prices, signals, holding_period=0)

    def test_maximum_drawdown_includes_initial_capital_peak(self):
        returns = pd.Series([-0.10, 0.05])
        self.assertAlmostEqual(calculate_maximum_drawdown(returns), -0.10)

    def test_entry_and_exit_costs_are_included_in_completed_trade_return(self):
        index = pd.date_range("2024-05-01", periods=4, freq="B")
        prices = pd.Series([100.0, 100.0, 110.0, 110.0], index=index)
        signals = pd.Series([1.0, np.nan, np.nan, np.nan], index=index)

        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=10.0,
            slippage_bps=0.0,
            holding_period=2,
        )

        daily = result["daily"]
        self.assertAlmostEqual(daily.loc[index[1], "trading_cost"], 0.001)
        self.assertAlmostEqual(daily.loc[index[3], "trading_cost"], 0.001)
        self.assertEqual(result["metrics"]["trades"], 1)
        self.assertEqual(result["trades"][0]["entry_date"], str(index[1]))
        self.assertEqual(result["trades"][0]["exit_date"], str(index[3]))
        expected = (1 - 0.001) * (1 + 0.10) * (1 - 0.001) - 1
        self.assertAlmostEqual(result["trades"][0]["return"], expected)

    def test_incomplete_final_horizon_block_is_not_entered_or_counted(self):
        index = pd.date_range("2024-06-01", periods=3, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0], index=index)
        signals = pd.Series([1.0, np.nan, np.nan], index=index)
        result = backtest_long_flat_strategy(
            prices, signals, transaction_cost_bps=10, slippage_bps=0, holding_period=2
        )
        self.assertEqual(result["metrics"]["trades"], 0)
        self.assertEqual(float(result["daily"]["trading_cost"].sum()), 0.0)


    def test_non_finite_or_negative_trade_friction_is_rejected(self):
        index = pd.date_range("2024-08-01", periods=4, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0], index=index)
        signals = pd.Series(1.0, index=index)
        for cost, slippage in ((-1.0, 0.0), (np.nan, 0.0), (0.0, np.inf)):
            with self.subTest(cost=cost, slippage=slippage):
                with self.assertRaisesRegex(ValueError, "finite non-negative"):
                    backtest_long_flat_strategy(
                        prices,
                        signals,
                        transaction_cost_bps=cost,
                        slippage_bps=slippage,
                    )

    def test_open_position_is_not_reported_as_completed_trade(self):
        index = pd.date_range("2024-09-01", periods=3, freq="B")
        execution_position = pd.Series([0.0, 1.0, 1.0], index=index)
        net_returns = pd.Series([0.0, -0.001, 0.02], index=index)
        self.assertEqual(extract_trades(execution_position, net_returns), [])

    def test_continuous_comparator_executes_next_close_and_liquidates_at_end(self):
        index = pd.date_range("2024-07-01", periods=5, freq="B")
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0], index=index)
        signals = pd.Series(1.0, index=index)
        result = backtest_long_flat_strategy(
            prices,
            signals,
            transaction_cost_bps=10,
            slippage_bps=0,
            non_overlapping_horizon=False,
        )
        daily = result["daily"]
        self.assertEqual(daily["position"].astype(int).tolist(), [0, 1, 1, 1])
        self.assertEqual(daily["execution_position"].astype(int).tolist(), [1, 1, 1, 0])
        self.assertEqual(result["metrics"]["trades"], 1)
        self.assertAlmostEqual(float(daily["trading_cost"].sum()), 0.002)


class WalkForwardExecutionGapTests(SimpleTestCase):
    def test_walk_forward_gap_is_horizon_plus_one(self):
        index = pd.RangeIndex(80)
        X = pd.DataFrame({"feature": np.arange(80.0)}, index=index)
        y = pd.Series(np.arange(80.0), index=index)
        folds = generate_walk_forward_splits(
            X,
            y,
            minimum_train_size=30,
            test_size=10,
            horizon=5,
            step_size=10,
        )
        fold = folds[0]
        self.assertEqual(fold["gap"], 6)
        self.assertEqual(fold["test_start"], fold["train_end"] + 6)


class WalkForwardTestWindowSizingTests(SimpleTestCase):
    def test_test_fold_contains_two_non_overlapping_one_month_forecasts(self):
        self.assertEqual(
            choose_walk_forward_test_size(100, horizon=20, default_test_size=200),
            50,
        )

    def test_medium_horizon_test_fold_is_expanded_to_fit_two_forecasts(self):
        self.assertEqual(
            choose_walk_forward_test_size(100, horizon=60, default_test_size=200),
            62,
        )

    def test_long_horizon_test_fold_is_expanded_to_fit_two_forecasts(self):
        # For H=252, the second forecast origin must be H+1 rows after the first.
        self.assertEqual(
            choose_walk_forward_test_size(254, horizon=252, default_test_size=200),
            254,
        )

    def test_test_fold_is_capped_by_available_oos_rows(self):
        self.assertEqual(
            choose_walk_forward_test_size(14, horizon=5, default_test_size=200),
            14,
        )

    def test_step_size_never_overlaps_long_horizon_test_windows(self):
        self.assertEqual(choose_walk_forward_step_size(254, default_step_size=200), 254)

    def test_step_size_preserves_default_spacing_for_shorter_folds(self):
        self.assertEqual(choose_walk_forward_step_size(100, default_step_size=200), 200)

    def test_generated_long_horizon_test_folds_do_not_overlap(self):
        X = pd.DataFrame({"feature": np.arange(1061, dtype=float)})
        y = pd.Series(np.arange(1061, dtype=float))
        test_size = choose_walk_forward_test_size(
            available_oos_observations=507,
            horizon=252,
            default_test_size=200,
        )
        step_size = choose_walk_forward_step_size(
            test_size=test_size,
            default_step_size=200,
        )
        folds = generate_walk_forward_splits(
            X,
            y,
            minimum_train_size=300,
            test_size=test_size,
            horizon=252,
            step_size=step_size,
        )
        self.assertGreaterEqual(len(folds), 2)
        self.assertGreaterEqual(folds[1]["test_start"], folds[0]["test_end"])

    def test_rejects_window_too_short_for_two_horizon_forecasts(self):
        with self.assertRaisesRegex(ValueError, "two non-overlapping"):
            choose_walk_forward_test_size(61, horizon=60, default_test_size=200)
