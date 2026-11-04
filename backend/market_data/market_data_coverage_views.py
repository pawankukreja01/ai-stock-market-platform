"""Fast, authenticated stored-market-data coverage (no provider calls)."""
from django.db.models import Max
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from stocks.models import Stock
from .models import HistoricalPrice, LatestQuote, Fundamental, NewsArticle


class MarketDataCoverageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prices = HistoricalPrice.objects.aggregate(latest_date=Max("date"))
        data = {
            "data_scope": "stored_database_only",
            "live_market_data": False,
            "stock_count": Stock.objects.filter(is_active=True).count(),
            "historical_price_count": HistoricalPrice.objects.count(),
            "last_historical_date": prices["latest_date"].isoformat()
                if prices["latest_date"] else None,
            "cached_quote_count": LatestQuote.objects.count(),
            "fundamental_record_count": Fundamental.objects.count(),
            "news_article_count": NewsArticle.objects.count(),
            "analyzed_news_count": NewsArticle.objects.exclude(
                sentiment_analyzed_at__isnull=True
            ).count(),
        }
        data["status"] = (
            "no_historical_prices" if data["historical_price_count"] == 0
            else "historical_data_available"
        )
        response = Response(data)
        response["Cache-Control"] = "private, no-store"
        return response
