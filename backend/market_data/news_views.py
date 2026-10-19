
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from market_data.models import NewsArticle
from market_data.serializers import NewsArticleSerializer


class NewsArticleListView(APIView):
    """
    Return stored news articles for a stock symbol.

    Example:
    /api/news/?symbol=AAPL&limit=10
    """

    def get(self, request):
        symbol = request.query_params.get("symbol", "").strip().upper()

        if not symbol:
            return Response(
                {"error": "The symbol query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"error": f"Stock '{symbol}' was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            return Response(
                {"error": "Limit must be an integer between 1 and 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= limit <= 100:
            return Response(
                {"error": "Limit must be between 1 and 100."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        articles = (
            NewsArticle.objects
            .filter(stock__symbol=symbol)
            .select_related("stock")
            .order_by(
                F("published_at").desc(nulls_last=True),
                "-retrieved_at",
            )[:limit]
        )

        serializer = NewsArticleSerializer(articles, many=True)

        return Response(
            {
                "symbol": symbol,
                "count": len(serializer.data),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
