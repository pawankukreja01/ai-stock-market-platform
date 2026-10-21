
from rest_framework.test import APISimpleTestCase

from .recommendation_serializers import (
    RecommendationRequestSerializer,
)


class RecommendationRequestSerializerTests(APISimpleTestCase):
    def setUp(self):
        self.valid_data = {
            "budget": "1000.00",
            "currency": "GBP",
            "risk_tolerance": "moderate",
            "horizon_months": 36,
            "market": "NASDAQ",
            "max_candidates": 20,
        }

    def test_valid_request(self):
        serializer = RecommendationRequestSerializer(
            data=self.valid_data
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["currency"],
            "GBP",
        )

    def test_currency_is_normalized(self):
        data = {**self.valid_data, "currency": "gbp"}

        serializer = RecommendationRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(
            serializer.validated_data["currency"],
            "GBP",
        )

    def test_zero_budget_is_rejected(self):
        data = {**self.valid_data, "budget": "0"}

        serializer = RecommendationRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("budget", serializer.errors)

    def test_invalid_risk_tolerance_is_rejected(self):
        data = {**self.valid_data, "risk_tolerance": "extreme"}

        serializer = RecommendationRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("risk_tolerance", serializer.errors)

    def test_candidate_limit_is_bounded(self):
        data = {**self.valid_data, "max_candidates": 101}

        serializer = RecommendationRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("max_candidates", serializer.errors)

    def test_horizon_must_be_positive(self):
        data = {**self.valid_data, "horizon_months": 0}

        serializer = RecommendationRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("horizon_months", serializer.errors)
