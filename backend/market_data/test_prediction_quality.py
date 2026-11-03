"""Regression tests for the meaning and safety of forecast evidence labels."""

from datetime import date, timedelta

import numpy as np
from django.test import SimpleTestCase

from market_data.prediction_quality import assess_prediction_evidence


class PredictionEvidenceTests(SimpleTestCase):
    def assess(self, actual, predicted, *, horizon=1, last_days_ago=1, coverage=0.90):
        return assess_prediction_evidence(
            y_train=np.full(100, 0.02),
            y_test=np.array(actual, dtype=float),
            predictions=np.array(predicted, dtype=float),
            horizon=horizon,
            last_price_date=date(2026, 11, 3) - timedelta(days=last_days_ago),
            as_of=date(2026, 11, 3),
            confidence=0.90,
            interval_coverage=coverage,
        )

    def test_strong_holdout_forecast_can_be_promising_but_never_live_ready(self):
        actual = np.full(40, 0.03)
        prediction = np.full(40, 0.029)
        report = self.assess(actual, prediction)
        self.assertEqual(report["status"], "promising_holdout_only")
        self.assertFalse(report["ready_for_live_trading"])
        self.assertTrue(report["beats_both_baselines_on_mae"])
        self.assertGreater(report["mae_skill_vs_best_baseline"], 0)
        self.assertEqual(report["holdout_observations"], 40)

    def test_weak_model_is_flagged_against_both_baselines(self):
        report = self.assess(np.zeros(40), np.full(40, 0.25))
        self.assertEqual(report["status"], "limited_evidence")
        self.assertFalse(report["beats_both_baselines_on_mae"])
        self.assertTrue(any("baseline" in w for w in report["warnings"]))
        # The zero-return baseline has zero error on this fixture; relative
        # improvement is mathematically undefined rather than negative infinity.
        self.assertIsNone(report["mae_skill_vs_best_baseline"])

    def test_negative_skill_when_baseline_has_nonzero_error(self):
        report = self.assess(np.full(40, 0.03), np.full(40, 0.25))
        self.assertLess(report["mae_skill_vs_best_baseline"], 0)

    def test_stale_prices_warn_without_inventing_recency(self):
        report = self.assess(np.full(40, 0.03), np.full(40, 0.029), last_days_ago=10)
        self.assertEqual(report["price_age_days"], 10)
        self.assertEqual(report["status"], "limited_evidence")
        self.assertTrue(any("seven calendar days" in w for w in report["warnings"]))

    def test_long_horizons_have_fewer_effective_windows(self):
        report = self.assess(np.full(100, 0.03), np.full(100, 0.029), horizon=20)
        self.assertEqual(report["approx_non_overlapping_holdout_windows"], 5)
        self.assertEqual(report["status"], "limited_evidence")

    def test_low_interval_coverage_warns(self):
        report = self.assess(np.full(40, 0.03), np.full(40, 0.029), coverage=0.55)
        self.assertTrue(any("coverage" in w for w in report["warnings"]))

    def test_future_dated_prices_warn(self):
        report = self.assess(np.full(40, 0.03), np.full(40, 0.029), last_days_ago=-2)
        self.assertEqual(report["status"], "limited_evidence")
        self.assertTrue(any("future-dated" in w for w in report["warnings"]))

    def test_rejects_invalid_holdout_inputs(self):
        with self.assertRaisesRegex(ValueError, "aligned"):
            self.assess([0.1, 0.2], [0.1])
        with self.assertRaisesRegex(ValueError, "finite"):
            self.assess([0.1] * 20, [float("nan")] * 20)
