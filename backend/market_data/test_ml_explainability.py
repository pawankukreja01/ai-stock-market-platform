
import numpy as np
import pandas as pd

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from ml_explainability import explain_prediction
from ml_models import (
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
)
from market_data.ml_views import MLReturnPredictionView


class ExplainPredictionTests(SimpleTestCase):
    """Test SHAP explanations with small synthetic datasets."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        rng = np.random.default_rng(42)
        observations = 120

        cls.features = pd.DataFrame(
            rng.normal(size=(observations, 4)),
            columns=[
                "momentum",
                "trend",
                "volatility",
                "volume_signal",
            ],
        )

        cls.target = (
            0.02 * cls.features["momentum"]
            + 0.015 * cls.features["trend"]
            - 0.01 * cls.features["volatility"]
            + 0.005 * cls.features["volume_signal"]
            + rng.normal(0, 0.002, observations)
        )

    def assert_model_explanation(self, model_factory):
        X_train = self.features.iloc[:80]
        y_train = self.target.iloc[:80]

        background = self.features.iloc[:80]
        instance = self.features.iloc[[80]]
        evaluation = self.features.iloc[81:111]

        model = model_factory()
        model.fit(X_train, y_train)

        explanation = explain_prediction(
            model=model,
            background_features=background,
            instance_features=instance,
            evaluation_features=evaluation,
            max_global_features=3,
        )

        # Basic explanation metadata.
        self.assertTrue(explanation["available"])
        self.assertEqual(explanation["method"], "SHAP")
        self.assertEqual(
            explanation["target"],
            "predicted_future_return",
        )

        # The reported prediction should match the fitted model.
        actual_prediction = float(model.predict(instance)[0])
        self.assertAlmostEqual(
            explanation["predicted_return"],
            actual_prediction,
            places=7,
        )

        # SHAP contributions should reconstruct the prediction.
        self.assertLess(
            abs(explanation["additivity_difference"]),
            1e-6,
        )

        # Local explanation should include every input feature.
        local = explanation["local_feature_contributions"]
        self.assertEqual(
            {item["feature"] for item in local},
            set(self.features.columns),
        )

        # Global importance should be non-empty and correctly ranked.
        global_importance = explanation["global_feature_importance"]
        self.assertGreater(len(global_importance), 0)
        self.assertLessEqual(len(global_importance), 3)

        importance_values = [
            item["mean_absolute_shap"]
            for item in global_importance
        ]

        self.assertEqual(
            importance_values,
            sorted(importance_values, reverse=True),
        )

        self.assertEqual(
            explanation["global_evaluation_rows"],
            len(evaluation),
        )

    def test_linear_regression_explanation(self):
        self.assert_model_explanation(
            create_linear_regression_model
        )

    def test_random_forest_explanation(self):
        self.assert_model_explanation(
            create_random_forest_model
        )

    def test_xgboost_explanation(self):
        self.assert_model_explanation(
            create_xgboost_model
        )


class MLPredictionValidationTests(SimpleTestCase):
    """Test API validation without requiring database records."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = MLReturnPredictionView.as_view()

    def test_missing_symbol_returns_bad_request(self):
        request = self.factory.get("/api/ml-prediction/")

        response = self.view(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"],
            "symbol is required.",
        )
