"""API endpoint for stocks-only research rankings."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .recommendation_serializers import RecommendationRequestSerializer
from .recommendation_engine import recommend_stocks
from .recommendation_allocation import allocate_whole_shares


class StockRecommendationsView(APIView):
    """
    Return research rankings for active stocks.

    GET /api/recommendations/?budget=1000&currency=USD
        &risk_tolerance=moderate&horizon_months=12
    """

    def get(self, request):
        serializer = RecommendationRequestSerializer(
            data=request.query_params
        )

        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = serializer.validated_data

        result = recommend_stocks(
            risk_tolerance=params["risk_tolerance"],
            market=params.get("market"),
            max_candidates=params["max_candidates"],
        )

        allocation = allocate_whole_shares(
            result.get("results", []),
            budget=params["budget"],
            currency=params["currency"],
            max_allocations=min(params["max_candidates"], 100),
        )

        response_data = dict(result)
        response_data["allocation"] = allocation
        response_data["request"] = {
            "budget": str(params["budget"]),
            "currency": params["currency"],
            "risk_tolerance": params["risk_tolerance"],
            "horizon_months": params["horizon_months"],
            "market": params.get("market"),
            "max_candidates": params["max_candidates"],
        }

        response_data["limitations"] = [
            "Recommendations are research rankings based on historical stored data, not financial advice or guarantees of future performance.",
            "Scores are relative to the available candidate universe and are not probabilities of profit.",
            "Stock prices and market data may be delayed, stale, incomplete, or inaccurate.",
            "Trading currency is sourced from Yahoo Finance metadata and is not independently verified; unknown or mismatched currencies are excluded from allocation.",
            "No currency conversion is performed. The stock's trading currency must match the requested budget currency.",
            "Allocation uses whole shares only and does not assume fractional-share support.",
            "Allocations are illustrative and are not executable orders or a guarantee of execution at the displayed prices.",
            "Allocation does not account for brokerage fees, transaction costs, taxes, bid-ask spreads, slippage, or settlement restrictions.",
            "The allocation process does not consider existing holdings, liabilities, emergency savings, or other personal financial circumstances.",
            "The budget is allocated using a simple ranking-based method; portfolio diversification and sector or concentration limits are not enforced.",
            "The investment horizon is recorded but is not incorporated into suitability scoring or allocation.",
            "Risk tolerance changes scoring weights but does not constitute a complete assessment of an investor's risk capacity or financial circumstances.",
            "Forecasts are not included in the recommendation scoring model.",
            "Sentiment scoring depends on the availability and quality of stored news articles and their sentiment analysis.",
            "Fundamental data may be incomplete, outdated, or incomparable across companies and sectors.",
            "The scoring weights and ranking methodology are provisional and have not been empirically validated.",
            "Historical returns, volatility, drawdowns, and other risk metrics do not reliably predict future performance.",
            "Allocation may leave uninvested cash when remaining funds cannot purchase another whole share within the budget.",
        ]


        return Response(response_data, status=status.HTTP_200_OK)
