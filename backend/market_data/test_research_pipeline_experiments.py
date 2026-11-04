"""Guard research-only experiments and published historical evidence."""
from io import StringIO
from unittest.mock import patch
import numpy as np
import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from market_data.forecast_reliability_views import (
    load_reliability_snapshot, ForecastReliabilityView,
)
from market_data.research_pipeline_experiments import (
    add_volatility_normalized_features, rolling_training_folds,
    ridge_factory, evaluate_pipeline_grid,
)


class PipelineResearchTests(SimpleTestCase):
    def test_normalization_preserves_original_return_and_dates(self):
        X = pd.DataFrame({
            "return_5d": [0.04, -0.02], "relative_return_5d": [0.01, -0.01],
            "volatility_20d": [0.10, 0.20],
        }, index=pd.bdate_range("2025-01-01", periods=2))
        Y = add_volatility_normalized_features(X)
        self.assertTrue(Y["return_5d"].equals(X["return_5d"]))
        self.assertTrue(Y.index.equals(X.index))
        self.assertAlmostEqual(Y.iloc[0]["return_5d_by_vol20"], 0.4)
        self.assertNotIn("return_5d_by_vol20", X)

    def test_invalid_trailing_volatility_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid historical"):
            add_volatility_normalized_features(
                pd.DataFrame({"return_5d": [0.1], "volatility_20d": [-0.1]})
            )

    def test_rolling_train_limits_do_not_move_test_dates_or_purge(self):
        folds = [{"train_start": 0, "train_end": 720, "test_start": 726,
                  "test_end": 826, "gap": 6, "train_size": 720}]
        capped = rolling_training_folds(folds, 500)
        self.assertEqual(capped[0]["train_start"], 220)
        self.assertEqual(capped[0]["test_start"], 726)
        self.assertEqual(folds[0]["train_start"], 0)

    def test_alpha_grid_fixed_in_advance(self):
        self.assertEqual(ridge_factory(1000).named_steps["model"].alpha, 1000)
        with self.assertRaises(ValueError):
            ridge_factory(1)

    def test_grid_matches_oos_dates_for_rolling_and_normalized_candidates(self):
        n = 770
        idx = pd.bdate_range("2022-01-03", periods=n)
        t = np.arange(n, dtype=float)
        X = pd.DataFrame({
            "return_5d": np.sin(t / 13) / 100,
            "volatility_20d": .2 + .01 * np.sin(t / 7),
        }, index=idx)
        y = pd.Series(np.cos(t / 17) / 100, index=idx)
        result = evaluate_pipeline_grid(
            {"price_volume": X,
             "price_volume_volatility_normalized": add_volatility_normalized_features(X)},
            y, horizon=5, min_train=300, test_size=60,
            windows=(None, 300), alphas=(100,),
        )
        self.assertEqual(len(result["candidates"]), 4)
        self.assertTrue(result["same_test_dates_and_targets"])
        self.assertEqual(
            len({r["out_of_sample_observations"] for r in result["candidates"]}), 1
        )
        self.assertEqual(
            len({(r["oos_start"], r["oos_end"]) for r in result["candidates"]}), 1
        )

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_original_db_fails_before_research(self):
        with self.assertRaisesRegex(CommandError, "Refusing research"):
            call_command("experiment_forecast_pipeline",
                         symbols=["AAPL"], as_of="2026-11-02",
                         output="/tmp/marketpulse-must-not-write.json",
                         stdout=StringIO())


class HistoricalReliabilityTests(SimpleTestCase):
    def test_snapshot_discloses_limits_and_true_historical_winner(self):
        report = load_reliability_snapshot()
        self.assertFalse(report["promotion_approved"])
        self.assertIsNone(report["uncertainty_coverage"])
        self.assertEqual(report["as_of"], "2026-11-02")
        self.assertEqual(len(report["stocks"]), 4)
        self.assertEqual(len(report["stocks"][0]["models"]), 4)
        nvda = next(s for s in report["stocks"] if s["symbol"] == "NVDA")
        self.assertEqual(
            [m["key"] for m in nvda["models"] if m["beats_all_baselines"]],
            ["zero_anchor_ridge"],
        )

    def test_unauthenticated_request_denied(self):
        response = ForecastReliabilityView.as_view()(
            APIRequestFactory().get("/api/forecast-reliability/")
        )
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_request_is_read_only_and_noncacheable(self):
        from django.contrib.auth import get_user_model
        request = APIRequestFactory().get("/api/forecast-reliability/")
        force_authenticate(request, user=get_user_model()(username="researcher"))
        response = ForecastReliabilityView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.data["kind"], "historical_research_snapshot")
