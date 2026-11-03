import numpy as np
import pandas as pd

from django.test import SimpleTestCase

from ml_engine import (
    build_stock_features,
    prepare_latest_feature_row,
    prepare_training_dataset,
)
from ml_uncertainty import chronological_three_way_split


class ChronologicalThreeWaySplitTests(SimpleTestCase):
    def make_data(self, observations=200):
        index = pd.RangeIndex(observations)
        X = pd.DataFrame(
            {"feature": np.arange(observations, dtype=float)},
            index=index,
        )
        y = pd.Series(
            np.arange(observations, dtype=float),
            index=index,
        )
        return X, y

    def test_horizon_gap_is_applied_at_both_boundaries(self):
        X, y = self.make_data(observations=200)

        (
            X_train,
            X_calibration,
            X_test,
            y_train,
            y_calibration,
            y_test,
        ) = chronological_three_way_split(
            X,
            y,
            train_size=0.70,
            calibration_size=0.15,
            horizon=5,
        )

        # The next-close execution convention requires H+1=6-row gaps.
        # 200 observations minus two 6-row gaps leaves 188.
        # Training takes 70% (131) and calibration takes 15% (28).
        self.assertEqual(X_train.index[-1], 130)
        self.assertEqual(X_calibration.index[0], 137)
        self.assertEqual(X_calibration.index[-1], 164)
        self.assertEqual(X_test.index[0], 171)

        self.assertTrue(X_train.index.equals(y_train.index))
        self.assertTrue(X_calibration.index.equals(y_calibration.index))
        self.assertTrue(X_test.index.equals(y_test.index))

        self.assertEqual(
            len(X),
            len(X_train)
            + len(X_calibration)
            + len(X_test)
            + 12,
        )

    def test_rejects_negative_horizon(self):
        X, y = self.make_data()

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            chronological_three_way_split(X, y, horizon=-1)

    def test_rejects_insufficient_data_after_gaps(self):
        X, y = self.make_data()

        with self.assertRaisesRegex(ValueError, "horizon gaps"):
            chronological_three_way_split(X, y, horizon=51)


class LatestFeatureRowTests(SimpleTestCase):
    def make_prices(self, observations=320):
        rng = np.random.default_rng(42)
        dates = pd.bdate_range("2025-01-01", periods=observations)
        close = 100.0 * np.exp(
            np.cumsum(
                rng.normal(
                    loc=0.0005,
                    scale=0.01,
                    size=observations,
                )
            )
        )
        volume = np.exp(
            rng.normal(
                loc=8.0,
                scale=0.2,
                size=observations,
            )
        )

        return pd.DataFrame(
            {
                "date": dates,
                "open_price": close,
                "high_price": close * 1.01,
                "low_price": close * 0.99,
                "close_price": close,
                "volume": volume,
            }
        )

    def test_latest_features_use_latest_price_date_without_targets(self):
        prices = self.make_prices()

        latest = prepare_latest_feature_row(prices)
        X, _ = prepare_training_dataset(prices, horizon=5)

        self.assertEqual(len(latest), 1)
        self.assertEqual(latest.index[-1], prices["date"].iloc[-1])
        self.assertEqual(list(latest.columns), list(X.columns))
        self.assertFalse(
            any(column.startswith("target_") for column in latest.columns)
        )
        self.assertTrue(np.isfinite(latest.to_numpy()).all())

    def test_incomplete_latest_features_raise_instead_of_using_stale_row(self):
        prices = self.make_prices()
        prices.loc[prices.index[-1], "volume"] = np.nan

        with self.assertRaisesRegex(
            ValueError,
            "latest observation is missing usable feature values",
        ):
            prepare_latest_feature_row(prices)

    def test_latest_features_reject_invalid_persisted_volume_flag(self):
        prices = self.make_prices()
        prices["is_ohlc_valid"] = True
        prices["is_volume_valid"] = True
        prices.loc[prices.index[-1], "is_volume_valid"] = False

        with self.assertRaisesRegex(
            ValueError,
            "latest observation is missing usable feature values",
        ):
            prepare_latest_feature_row(prices)


class NextCloseTargetTimingTests(SimpleTestCase):
    def make_prices(self, observations=330):
        dates = pd.bdate_range("2024-01-01", periods=observations)
        close = pd.Series(np.arange(observations, dtype=float) + 100.0)
        return pd.DataFrame({
            "date": dates,
            "open_price": close.to_numpy(),
            "high_price": close.to_numpy() + 1.0,
            "low_price": close.to_numpy() - 1.0,
            "close_price": close.to_numpy(),
            "volume": np.full(observations, 1000.0),
        })

    def test_horizon_target_starts_at_next_session_close(self):
        prices = self.make_prices()
        features = build_stock_features(prices)
        horizon = 5
        origin = 210
        expected = (
            prices["close_price"].iloc[origin + horizon + 1]
            / prices["close_price"].iloc[origin + 1]
        ) - 1
        self.assertAlmostEqual(
            features[f"target_{horizon}d"].loc[prices["date"].iloc[origin]],
            expected,
        )

    def test_invalid_next_session_entry_candle_invalidates_target(self):
        prices = self.make_prices()
        prices["is_ohlc_valid"] = True
        origin = 210
        prices.loc[origin + 1, "is_ohlc_valid"] = False
        features = build_stock_features(prices)
        self.assertTrue(pd.isna(features.loc[prices["date"].iloc[origin], "target_5d"]))

    def test_invalid_horizon_exit_candle_invalidates_target(self):
        prices = self.make_prices()
        prices["is_ohlc_valid"] = True
        origin = 210
        prices.loc[origin + 6, "is_ohlc_valid"] = False
        features = build_stock_features(prices)
        self.assertTrue(pd.isna(features.loc[prices["date"].iloc[origin], "target_5d"]))
