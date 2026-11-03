from datetime import date
import numpy as np
import pandas as pd
from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from market_data.management.commands.validate_stock_forecasts import (
    model_beats_all_baselines,
    common_calendar_window,
    build_model_scorecard,
    render_model_scorecard,
)


class ModelVersusBaselineTests(SimpleTestCase):
    def report(self, selected=0.01, zero=0.02, mean=0.03, momentum=0.04):
        return {
            "metrics": {
                "selected_model": {"mae": selected},
                "zero_return": {"mae": zero},
                "historical_mean": {"mae": mean},
                "momentum": {"mae": momentum},
            }
        }

    def test_all_three_baselines_must_be_beaten(self):
        self.assertTrue(model_beats_all_baselines(self.report()))
        self.assertFalse(
            model_beats_all_baselines(self.report(momentum=0.005))
        )
        self.assertFalse(
            model_beats_all_baselines(self.report(zero=0.01))
        )

    def test_missing_metrics_are_not_treated_as_wins(self):
        self.assertFalse(
            model_beats_all_baselines(self.report(selected=None))
        )
        self.assertFalse(
            model_beats_all_baselines(self.report(momentum=None))
        )


class CommonWindowTests(SimpleTestCase):
    def test_returns_intersection_of_historical_date_ranges(self):
        bounds = [
            {"first": date(2020, 1, 1), "last": date(2026, 11, 3)},
            {"first": date(2022, 1, 1), "last": date(2026, 10, 30)},
            {"first": date(2021, 1, 1), "last": date(2026, 10, 31)},
        ]
        self.assertEqual(
            common_calendar_window(bounds),
            (date(2022, 1, 1), date(2026, 10, 30)),
        )

    def test_rejects_non_overlapping_histories(self):
        with self.assertRaisesRegex(ValueError, "common calendar"):
            common_calendar_window([
                {"first": date(2020, 1, 1), "last": date(2020, 12, 31)},
                {"first": date(2022, 1, 1), "last": date(2022, 12, 31)},
            ])

    def test_rejects_missing_history(self):
        with self.assertRaisesRegex(ValueError, "dated historical"):
            common_calendar_window([
                {"first": None, "last": None},
            ])


class ModelScorecardTests(SimpleTestCase):
    def report(self, model_mae=0.032, zero_mae=0.031,
               mean_mae=0.034, momentum_mae=0.037,
               balanced_direction=0.49, specificity=0.12):
        return {
            "metrics": {
                "selected_model": {
                    "mae": model_mae,
                    "balanced_directional_accuracy": balanced_direction,
                    "negative_specificity": specificity,
                    "predicted_positive_rate": 0.966,
                    "actual_positive_rate": 0.558,
                    "observations": 500,
                },
                "zero_return": {"mae": zero_mae},
                "historical_mean": {"mae": mean_mae},
                "momentum": {"mae": momentum_mae},
            }
        }

    def test_reports_error_in_percentage_points_and_best_baseline(self):
        scorecard = build_model_scorecard(self.report())
        self.assertEqual(scorecard["best_baseline"], "zero_return")
        self.assertEqual(scorecard["mae_percent"], 3.2)
        self.assertEqual(scorecard["best_baseline_mae_percent"], 3.1)
        self.assertEqual(
            scorecard["mae_improvement_vs_best_baseline_percentage_points"], -0.1
        )
        self.assertEqual(
            scorecard["baselines_beaten_on_mae"],
            ["historical_mean", "momentum"],
        )
        self.assertEqual(scorecard["balanced_directional_accuracy_percent"], 49.0)
        self.assertEqual(scorecard["negative_specificity_percent"], 12.0)
        self.assertIn("improvement -0.100 percentage points",
                      render_model_scorecard(scorecard))

    def test_missing_direction_metrics_have_safe_output(self):
        scorecard = build_model_scorecard(
            self.report(balanced_direction=None, specificity=None)
        )
        self.assertIn(
            "balanced direction unavailable", render_model_scorecard(scorecard)
        )

    def test_model_below_best_baseline_has_positive_improvement(self):
        scorecard = build_model_scorecard(self.report(model_mae=0.029))
        self.assertEqual(
            scorecard["mae_improvement_vs_best_baseline_percentage_points"], 0.2
        )
        self.assertEqual(len(scorecard["baselines_beaten_on_mae"]), 3)

    def test_unavailable_baselines_do_not_produce_fake_score(self):
        scorecard = build_model_scorecard(self.report(
            model_mae=None, zero_mae=None, mean_mae=None, momentum_mae=None
        ))
        self.assertIsNone(scorecard["best_baseline"])
        self.assertIn("insufficient", render_model_scorecard(scorecard))


class ConservativeResearchModelTests(SimpleTestCase):
    def test_research_models_train_and_predict_on_finite_data(self):
        from market_data.management.commands.validate_stock_forecasts import MODEL_FACTORIES
        X = pd.DataFrame({
            "return_1d": np.sin(np.arange(80) / 7.0),
            "return_5d": np.cos(np.arange(80) / 10.0),
            "trend_ratio": np.arange(80) / 100.0,
        })
        y = pd.Series(np.sin(np.arange(80) / 5.0) / 100.0)
        for model_name in ("conservative_forest", "zero_anchor_ridge"):
            with self.subTest(model=model_name):
                model = MODEL_FACTORIES[model_name]()
                model.fit(X.iloc[:60], y.iloc[:60])
                predictions = model.predict(X.iloc[60:])
                self.assertEqual(len(predictions), 20)
                self.assertTrue(np.isfinite(predictions).all())

    def test_zero_anchor_ridge_does_not_learn_bullish_intercept(self):
        from ml_models import create_zero_anchor_ridge_model
        X = pd.DataFrame({"signal": [0.0] * 60})
        y = pd.Series([0.08] * 60)
        model = create_zero_anchor_ridge_model()
        model.fit(X, y)
        result = model.predict(pd.DataFrame({"signal": [0.0]}))
        self.assertAlmostEqual(float(result[0]), 0.0, places=8)

    def test_invalid_as_of_argument_is_rejected_early(self):
        with self.assertRaisesRegex(CommandError, "YYYY-MM-DD"):
            call_command(
                "validate_stock_forecasts",
                symbols=["AAPL"],
                as_of="not-a-date",
                stdout=StringIO(),
            )

    def test_future_as_of_argument_is_rejected_early(self):
        with self.assertRaisesRegex(CommandError, "future"):
            call_command(
                "validate_stock_forecasts",
                symbols=["AAPL"],
                as_of="2099-01-01",
                stdout=StringIO(),
            )
