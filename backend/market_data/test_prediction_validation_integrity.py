import numpy as np
import pandas as pd
from django.test import SimpleTestCase

from ml_pipeline import chronological_purged_train_test_split
from ml_uncertainty import calculate_calibration_error_quantile


class PurgedExperimentSplitTests(SimpleTestCase):
    def test_horizon_gap_separates_training_labels_from_test_origins(self):
        X = pd.DataFrame({"feature": np.arange(100.0)})
        y = pd.Series(np.arange(100.0))
        X_train, X_test, y_train, y_test = chronological_purged_train_test_split(
            X, y, test_size=0.2, gap=5
        )
        self.assertEqual(X_train.index[-1], 74)
        self.assertEqual(X_test.index[0], 80)
        self.assertEqual(y_train.index[-1], 74)
        self.assertEqual(y_test.index[0], 80)
        self.assertEqual(len(X), len(X_train) + len(X_test) + 5)

    def test_rejects_invalid_gap(self):
        X = pd.DataFrame({"feature": np.arange(20.0)})
        y = pd.Series(np.arange(20.0))
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            chronological_purged_train_test_split(X, y, gap=-1)


class FiniteSampleCalibrationTests(SimpleTestCase):
    def test_uses_finite_sample_conformal_order_statistic(self):
        actual = np.zeros(10)
        predicted = np.arange(1, 11, dtype=float) / 100
        # ceil((10 + 1) * 0.80) = 9; ninth sorted absolute error is 0.09.
        margin = calculate_calibration_error_quantile(
            actual, predicted, confidence=0.80
        )
        self.assertAlmostEqual(margin, 0.09)

    def test_returns_no_finite_interval_when_required_rank_exceeds_sample(self):
        actual = np.zeros(10)
        predicted = np.arange(1, 11, dtype=float) / 100
        # ceil((10 + 1) * 0.99) = 11, beyond the ten available errors.
        self.assertIsNone(
            calculate_calibration_error_quantile(
                actual, predicted, confidence=0.99
            )
        )
