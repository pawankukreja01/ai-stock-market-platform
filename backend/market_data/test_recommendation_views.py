
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase


class StockRecommendationsViewTests(APITestCase):
    url = "/api/recommendations/"

    def valid_params(self):
        return {
            "budget": "1000.00",
            "currency": "USD",
            "risk_tolerance": "moderate",
            "horizon_months": 12,
            "market": "NASDAQ",
            "max_candidates": 10,
        }

    @patch("market_data.recommendation_views.recommend_stocks")
    def test_valid_request_returns_rankings_and_limitations(
        self, mock_recommend
    ):
        mock_recommend.return_value = {
            "risk_tolerance": "moderate",
            "candidate_universe_size": 3,
            "eligible_candidate_count": 2,
            "scored_candidate_count": 2,
            "scoring_weights": {},
            "forecast_included": False,
            "results": [],
            "disclaimer": "Research rankings only.",
        }

        response = self.client.get(self.url, self.valid_params())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["request"]["budget"], "1000.00")
        self.assertEqual(response.data["request"]["currency"], "USD")
        self.assertEqual(response.data["request"]["horizon_months"], 12)
        self.assertFalse(response.data["forecast_included"])
        self.assertTrue(response.data["limitations"])

        mock_recommend.assert_called_once_with(
            risk_tolerance="moderate",
            market="NASDAQ",
            max_candidates=10,
        )

    def test_invalid_risk_tolerance_returns_400(self):
        params = self.valid_params()
        params["risk_tolerance"] = "extreme"

        response = self.client.get(self.url, params)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

    def test_zero_budget_returns_400(self):
        params = self.valid_params()
        params["budget"] = "0"

        response = self.client.get(self.url, params)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_horizon_returns_400(self):
        params = self.valid_params()
        params["horizon_months"] = 0

        response = self.client.get(self.url, params)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("market_data.recommendation_views.recommend_stocks")
    def test_currency_is_normalised(self, mock_recommend):
        mock_recommend.return_value = {
            "risk_tolerance": "moderate",
            "candidate_universe_size": 0,
            "eligible_candidate_count": 0,
            "scored_candidate_count": 0,
            "scoring_weights": {},
            "forecast_included": False,
            "results": [],
            "disclaimer": "Research rankings only.",
        }

        params = self.valid_params()
        params["currency"] = "usd"

        response = self.client.get(self.url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["request"]["currency"], "USD")
        self.assertEqual(response.data["allocation"]["currency"], "USD")

    @patch("market_data.recommendation_views.recommend_stocks")
    def test_valid_request_includes_budget_allocation(self, mock_recommend):
        mock_recommend.return_value = {
            "risk_tolerance": "moderate",
            "candidate_universe_size": 1,
            "eligible_candidate_count": 1,
            "scored_candidate_count": 1,
            "scoring_weights": {},
            "forecast_included": False,
            "results": [
                {
                    "symbol": "AAA",
                    "company_name": "Example A",
                    "exchange": "NASDAQ",
                    "currency": "USD",
                    "latest_price": "100.00",
                    "rank": 1,
                    "score": 90,
                }
            ],
            "disclaimer": "Research rankings only.",
        }

        response = self.client.get(self.url, self.valid_params())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("allocation", response.data)

        allocation = response.data["allocation"]

        self.assertEqual(allocation["currency"], "USD")
        self.assertEqual(allocation["budget"], "1000.00")
        self.assertEqual(allocation["invested"], "1000.00")
        self.assertEqual(allocation["remaining_cash"], "0.00")
        self.assertFalse(allocation["fractional_shares_used"])
        self.assertEqual(allocation["excluded"], [])

        self.assertEqual(len(allocation["allocations"]), 1)

        item = allocation["allocations"][0]
        self.assertEqual(item["symbol"], "AAA")
        self.assertEqual(item["shares"], 10)
        self.assertEqual(item["latest_price"], "100.00")
        self.assertEqual(item["estimated_cost"], "1000.00")
        self.assertEqual(item["rank"], 1)

    @patch("market_data.recommendation_views.recommend_stocks")
    def test_mismatched_currency_is_excluded(self, mock_recommend):
        mock_recommend.return_value = {
            "risk_tolerance": "moderate",
            "candidate_universe_size": 1,
            "eligible_candidate_count": 1,
            "scored_candidate_count": 1,
            "scoring_weights": {},
            "forecast_included": False,
            "results": [
                {
                    "symbol": "BBB",
                    "company_name": "Example B",
                    "exchange": "LSE",
                    "currency": "GBP",
                    "latest_price": "50.00",
                    "rank": 1,
                    "score": 85,
                }
            ],
            "disclaimer": "Research rankings only.",
        }

        response = self.client.get(self.url, self.valid_params())

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        allocation = response.data["allocation"]
        self.assertEqual(allocation["currency"], "USD")
        self.assertEqual(allocation["invested"], "0.00")
        self.assertEqual(allocation["remaining_cash"], "1000.00")
        self.assertEqual(allocation["allocations"], [])
        self.assertEqual(len(allocation["excluded"]), 1)
        self.assertEqual(allocation["excluded"][0]["symbol"], "BBB")