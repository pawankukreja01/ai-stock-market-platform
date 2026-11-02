import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml_engine import build_stock_features
from ml_engine import build_stock_features, calculate_rsi


class PriceQualityFeatureTests(SimpleTestCase):
    def make_prices(self, observations=320):
        dates = pd.bdate_range("2024-01-01", periods=observations)
        close = 100.0 + np.arange(observations, dtype=float) * 0.1

        return pd.DataFrame({
            "date": dates,
            "high_price": close * 1.01,
            "low_price": close * 0.99,
            "close_price": close,
            "volume": np.full(observations, 100_000.0),
        })

    def test_invalid_candle_has_no_features_or_targets(self):
        prices = self.make_prices()
        bad_index = 280
        prices.loc[bad_index, "high_price"] = (
            prices.loc[bad_index, "close_price"] * 0.8
        )

        features = build_stock_features(prices)

        self.assertTrue(features.loc[prices.loc[bad_index, "date"]].isna().all())

    def test_future_target_is_missing_when_path_crosses_invalid_candle(self):
        prices = self.make_prices()
        bad_index = 280
        prices.loc[bad_index, "close_price"] = np.nan

        features = build_stock_features(prices)
        dates = pd.to_datetime(prices["date"])

        # The target at bad_index - 5 would cross the invalid close
        # at its five-session endpoint.
        origin_date = dates.iloc[bad_index - 5]
        self.assertTrue(pd.isna(features.loc[origin_date, "target_5d"]))

        # The target beginning at the invalid candle must also be missing.
        bad_date = dates.iloc[bad_index]
        self.assertTrue(pd.isna(features.loc[bad_date, "target_5d"]))

    def test_valid_candles_keep_finite_short_horizon_targets(self):
        prices = self.make_prices()
        features = build_stock_features(prices)

        target = features["target_5d"].dropna()
        self.assertGreater(len(target), 0)
        self.assertTrue(np.isfinite(target.to_numpy()).all())

    def test_persisted_invalid_ohlc_flag_masks_feature_row(self):
        prices = self.make_prices()
        prices["is_ohlc_valid"] = True
        bad_index = 280
        prices.loc[bad_index, "is_ohlc_valid"] = False

        features = build_stock_features(prices)
        bad_date = pd.to_datetime(prices.loc[bad_index, "date"])

        self.assertTrue(features.loc[bad_date].isna().all())

    def test_open_price_is_validated_when_column_is_present(self):
        prices = self.make_prices()
        prices["open_price"] = prices["close_price"]
        bad_index = 280
        prices.loc[bad_index, "open_price"] = (
            prices.loc[bad_index, "high_price"] * 1.1
        )

        features = build_stock_features(prices)
        bad_date = pd.to_datetime(prices.loc[bad_index, "date"])

        self.assertTrue(features.loc[bad_date].isna().all())

    def test_invalid_volume_flag_masks_volume_features_only(self):
        prices = self.make_prices()
        prices["is_volume_valid"] = True
        bad_index = 280
        prices.loc[bad_index, "is_volume_valid"] = False

        features = build_stock_features(prices)
        bad_date = pd.to_datetime(prices.loc[bad_index, "date"])

        self.assertTrue(pd.isna(features.loc[bad_date, "volume_change_1d"]))
        self.assertTrue(pd.isna(features.loc[bad_date, "relative_volume_20d"]))
        self.assertTrue(np.isfinite(features.loc[bad_date, "rsi_14"]))
        self.assertTrue(np.isfinite(features.loc[bad_date, "sma20_ratio"]))


    def test_rsi_is_100_when_prices_only_rise(self):
        prices = pd.Series(
            np.arange(1, 31, dtype=float)
        )

        rsi = calculate_rsi(prices, period=14)

        self.assertAlmostEqual(
            float(rsi.iloc[-1]),
            100.0,
        )

    def test_rsi_is_zero_when_prices_only_fall(self):
        prices = pd.Series(
            np.arange(30, 0, -1, dtype=float)
        )

        rsi = calculate_rsi(prices, period=14)

        self.assertAlmostEqual(
            float(rsi.iloc[-1]),
            0.0,
        )

    def test_rsi_is_50_when_prices_are_unchanged(self):
        prices = pd.Series(
            np.full(30, 100.0)
        )

        rsi = calculate_rsi(prices, period=14)

        self.assertAlmostEqual(
            float(rsi.iloc[-1]),
            50.0,
        )
