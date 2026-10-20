import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml_engine import build_stock_features


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
