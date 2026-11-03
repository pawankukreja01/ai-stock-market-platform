from datetime import date
from django.test import SimpleTestCase

from market_data.management.commands.validate_stock_forecasts import (
    model_beats_all_baselines,
    common_calendar_window,
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
