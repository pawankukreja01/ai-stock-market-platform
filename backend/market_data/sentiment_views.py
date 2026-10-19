
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from market_data.models import NewsArticle


SENTIMENT_LABELS = ("positive", "neutral", "negative")


class StockSentimentSummaryView(APIView):
    """
    Summarize stored news sentiment for one stock.

    Example:
    /api/sentiment/?symbol=AAPL&limit=50
    """

    def get(self, request):
        symbol = request.query_params.get("symbol", "").strip().upper()

        if not symbol:
            return Response(
                {"error": "The symbol query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {"error": f"Stock '{symbol}' was not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            return Response(
                {"error": "Limit must be an integer between 1 and 500."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not 1 <= limit <= 500:
            return Response(
                {"error": "Limit must be between 1 and 500."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        articles = list(
            NewsArticle.objects.filter(
                stock=stock,
                sentiment_analyzed_at__isnull=False,
                sentiment_label__in=SENTIMENT_LABELS,
            )
            .order_by(
                F("published_at").desc(nulls_last=True),
                "-retrieved_at",
            )[:limit]
        )

        total = len(articles)

        counts = {
            label: sum(
                article.sentiment_label == label
                for article in articles
            )
            for label in SENTIMENT_LABELS
        }

        distribution = {
            label: {
                "count": counts[label],
                "percentage": (
                    round(counts[label] / total * 100, 2)
                    if total
                    else 0.0
                ),
            }
            for label in SENTIMENT_LABELS
        }

        scores = [
            article.sentiment_score
            for article in articles
            if article.sentiment_score is not None
        ]

        average_score = (
            round(sum(scores) / len(scores), 6)
            if scores
            else None
        )

        analysis_times = [
            article.sentiment_analyzed_at
            for article in articles
            if article.sentiment_analyzed_at is not None
        ]

        latest_analysis_at = (
            max(analysis_times) if analysis_times else None
        )

        return Response(
            {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "articles_analyzed": total,
                "articles_with_scores": len(scores),
                "sentiment_distribution": distribution,
                "average_sentiment_score": average_score,
                "latest_analysis_at": latest_analysis_at,
            },
            status=status.HTTP_200_OK,
        )
