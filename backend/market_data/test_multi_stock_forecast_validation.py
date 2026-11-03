from django.test import SimpleTestCase

from market_data.management.commands.validate_stock_forecasts import (
    model_beats_all_baselines,
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
