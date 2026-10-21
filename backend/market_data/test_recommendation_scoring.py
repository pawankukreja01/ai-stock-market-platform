
from django.test import SimpleTestCase

from .recommendation_scoring import (
    calculate_weighted_score,
    percentile_ranks,
    score_candidate,
)


class RecommendationScoringTests(SimpleTestCase):
    def test_percentile_ranks_preserve_missing_values(self):
        result = percentile_ranks([10, None, 30])

        self.assertEqual(result[0], 0.0)
        self.assertIsNone(result[1])
        self.assertEqual(result[2], 100.0)

    def test_lower_is_better_can_be_used_for_risk(self):
        result = percentile_ranks(
            [10, 30],
            higher_is_better=False,
        )

        self.assertEqual(result, [100.0, 0.0])

    def test_equal_values_receive_equal_percentiles(self):
        result = percentile_ranks([5, 5, 5])

        self.assertEqual(result, [50.0, 50.0, 50.0])

    def test_score_requires_at_least_three_components(self):
        result = calculate_weighted_score({
            "momentum": 80,
            "sentiment": 60,
        })

        self.assertIsNone(result)

    def test_score_uses_available_components(self):
        result = calculate_weighted_score({
            "momentum": 80,
            "fundamentals": 60,
            "risk_adjusted": 70,
        })

        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 100)

    def test_ineligible_candidate_never_receives_score(self):
        result = score_candidate(
            {
                "momentum": 90,
                "fundamentals": 90,
                "risk_adjusted": 90,
            },
            eligible=False,
            reasons=["Price data is stale."],
        )

        self.assertIsNone(result["score"])
        self.assertFalse(result["eligible"])
        self.assertIn("Price data is stale.", result["reasons"])

    def test_insufficient_data_is_not_scored(self):
        result = score_candidate({
            "momentum": 80,
            "sentiment": None,
        })

        self.assertIsNone(result["score"])
        self.assertFalse(result["eligible"])
