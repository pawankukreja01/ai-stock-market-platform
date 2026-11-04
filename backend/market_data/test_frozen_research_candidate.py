"""Frozen hypothesis tests; never require or mutate the user's research data."""
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from market_data.frozen_research_candidate import (
    FROZEN_SPEC, PRICE_VOLUME_FEATURE_COLUMNS, validate_frozen_feature_schema,\n    evaluate_frozen_candidate, load_frozen_spec,
)
from market_data.management.commands.experiment_forecast_pipeline import load_locked_cohort
from market_data.management.commands.validate_frozen_forecast_candidate import summarize_horizon


class FrozenCandidateProtocolTests(SimpleTestCase):
    def test_lock_has_expected_fixed_research_parameters(self):
        spec, digest = load_frozen_spec()
        self.assertEqual(spec, FROZEN_SPEC)
        self.assertEqual(len(digest), 64)
        self.assertEqual(spec["ridge_alpha"], 1000)
        self.assertFalse(spec["ridge_fit_intercept"])
        self.assertEqual(spec["training_window"], "expanding")
        self.assertEqual(spec["feature_set"], "price_volume")
        self.assertEqual(spec["horizons_trading_days"], [1, 5, 20, 60])
        self.assertFalse(spec["approved_for_live_prediction"])

    def test_changed_candidate_parameters_fail_closed(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "candidate.json"
            path.write_text(json.dumps(dict(FROZEN_SPEC, ridge_alpha=100)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "lock mismatch"):
                load_frozen_spec(path)

    def test_rejects_unlisted_horizon_and_market_relative_features(self):
        dates = pd.bdate_range("2022-01-03", periods=940)
        t = np.arange(len(dates), dtype=float)
        X = pd.DataFrame({"return_5d": .01 * np.sin(t / 10),
                          "volatility_20d": np.full(len(t), .2)}, index=dates)
        y = pd.Series(.005 * np.cos(t / 17), index=dates)
        with self.assertRaisesRegex(ValueError, "not part of the frozen"):
            evaluate_frozen_candidate(X, y, horizon=12)
        with self.assertRaisesRegex(ValueError, "price/volume-only"):
            evaluate_frozen_candidate(X.assign(relative_return_5d=0), y, horizon=5)

    def test_accepts_exact_original_18_feature_columns(self):
        self.assertEqual(len(PRICE_VOLUME_FEATURE_COLUMNS), 18)
        self.assertIn("relative_volume_20d", PRICE_VOLUME_FEATURE_COLUMNS)
        X = pd.DataFrame(columns=list(PRICE_VOLUME_FEATURE_COLUMNS))
        self.assertIsNone(validate_frozen_feature_schema(X))

    def test_rejects_market_relative_returns_but_not_relative_volume(self):
        X = pd.DataFrame(columns=list(PRICE_VOLUME_FEATURE_COLUMNS))
        with self.assertRaisesRegex(ValueError, "relative_return_5d"):
            validate_frozen_feature_schema(
                X.assign(relative_return_5d=0.0)
            )
        with self.assertRaisesRegex(ValueError, "order_mismatch=True"):
            validate_frozen_feature_schema(X[list(reversed(X.columns))])

    def test_frozen_model_with_full_raw_volume_feature_schema(self):
        dates = pd.bdate_range("2022-01-03", periods=940)
        timeline = np.arange(len(dates), dtype=float)
        data = {
            key: 0.01 * np.sin(timeline / 15.0 + i / 8.0)
            for i, key in enumerate(PRICE_VOLUME_FEATURE_COLUMNS)
        }
        X = pd.DataFrame(data, index=dates)
        y = pd.Series(0.005 * np.cos(timeline / 17.0), index=dates)
        result = evaluate_frozen_candidate(X, y, horizon=5)
        self.assertEqual(result["status"], "evaluated")
        self.assertEqual(result["out_of_sample_observations"], 400)

    def test_frozen_pipeline_uses_unchanged_purged_folds(self):
        dates = pd.bdate_range("2022-01-03", periods=940)
        t = np.arange(len(dates), dtype=float)
        X = pd.DataFrame({
            name: .01 * np.sin(t / 10 + i / 12)
            for i, name in enumerate(PRICE_VOLUME_FEATURE_COLUMNS)
        }, index=dates)
        y = pd.Series(.005 * np.cos(t / 17), index=dates)
        result = evaluate_frozen_candidate(X, y, horizon=5)
        self.assertEqual(result["status"], "evaluated")
        self.assertGreaterEqual(result["folds"], 3)
        self.assertGreaterEqual(result["out_of_sample_observations"], 300)
        self.assertEqual(result["historical_window_role"],
                         "development_diagnostic_not_independent_holdout")
        self.assertEqual(set(result["baselines"]),
                         {"zero_return", "historical_mean", "momentum"})

    def test_recovered_original_33_stock_manifest_is_immutable(self):
        manifest = Path(__file__).parent / "research_cohorts" / "raw_adjusted_33_stock_v1.json"
        symbols, digest = load_locked_cohort(manifest)
        self.assertEqual(len(symbols), 33)
        self.assertEqual(digest,
                         "8ceac6b8b1d1ada47a719f97ab29c398696d1b28211c27523e7d963d4739e345")
        self.assertEqual(symbols[:5], ["AAPL", "AMD", "AMT", "BP.L", "BT-A.L"])
        self.assertEqual(symbols[-5:], ["SVT.L", "TGT", "TSCO.L", "TSLA", "VZ"])

    def test_original_cohort_file_must_contain_33_distinct_symbols(self):
        with TemporaryDirectory() as d:
            path = Path(d) / "cohort.json"
            path.write_text(json.dumps({"symbols": ["AAPL", "MSFT"]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly 33"):
                load_locked_cohort(path)
            path.write_text(json.dumps({"symbols": ["AAPL"] * 33}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_locked_cohort(path)

    def test_summary_excludes_missing_horizon_data(self):
        ok = {"status": "evaluated", "beats_all_baselines_on_mae": True,
              "scorecard": {"mae_improvement_vs_best_baseline_percentage_points": .07}}
        missing = {"status": "insufficient_or_invalid_data", "reason": "Too short"}
        result = summarize_horizon([
            {"horizons": {"5": ok}}, {"horizons": {"5": missing}},
        ], 5)
        self.assertEqual(result["stocks_evaluated"], 1)
        self.assertEqual(result["stocks_excluded"], 1)
        self.assertEqual(result["stocks_beating_all_three_baselines"], 1)
        self.assertFalse(result["deployment_approved"])

    @patch.dict("os.environ", {"DB_NAME": "ai_stock_market"})
    def test_original_db_fails_before_reading_cohort_or_writing_file(self):
        with TemporaryDirectory() as d:
            output = Path(d) / "should-not-exist.json"
            with self.assertRaisesRegex(CommandError, "Refusing frozen research"):
                call_command(
                    "validate_frozen_forecast_candidate",
                    cohort_file="/tmp/nonexistent-research-cohort.json",
                    as_of="2026-11-02",
                    output=str(output), stdout=StringIO(),
                )
            self.assertFalse(output.exists())
