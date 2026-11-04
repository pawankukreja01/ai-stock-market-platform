"""Stored latest quote endpoint with explicit historic-archive fallback.

The preview's offline historical archive never masquerades as a current quote.
"""
from datetime import datetime, time, timezone as dt_timezone
from decimal import Decimal
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from stocks.models import Stock
from .models import HistoricalPrice, LatestQuote
from .quote_serializers import LatestQuoteSerializer


def archived_quote_payload(stock):
    """Describe the newest real stored daily OHLC close; do not call Yahoo."""
    observations = list(
        HistoricalPrice.objects.filter(
            stock=stock,
            close_price__gt=0,
            is_ohlc_valid=True,
        ).order_by("-date", "-pk")[:2]
    )
    if not observations:
        return None
    latest = observations[0]
    previous = observations[1] if len(observations) > 1 else None
    # The stored price has already been normalized by the ingestion pipeline.
    # Never infer a currency from a ticker suffix when provenance is missing.
    currency = latest.storage_currency or stock.currency
    change = latest.close_price - previous.close_price if previous else None
    change_pct = (
        (change / previous.close_price * Decimal("100")).quantize(Decimal("0.01"))
        if previous and previous.close_price > 0 else None
    )
    return {
        "id": None,
        "symbol": stock.symbol,
        "company_name": stock.company_name,
        "exchange": stock.exchange,
        "provider_currency": latest.provider_currency or "",
        "price": str(latest.close_price),
        "previous_close": str(previous.close_price) if previous else None,
        "change": str(change) if change is not None else None,
        "change_percent": str(change_pct) if change_pct is not None else None,
        "volume": latest.volume,
        "currency": currency,
        "provider": "stored_historical_archive",
        "quote_type": "daily_close",
        "source_timestamp": datetime.combine(latest.date, time.min, tzinfo=dt_timezone.utc).isoformat(),
        "retrieved_at": None,
        "freshness_status": "stale",
        "data_note": (
            f"ARCHIVED DAILY CLOSE dated {latest.date.isoformat()}, taken from "
            "historical stored observations. Not a current or real-time quote; "
            "the displayed change compares the previous stored close."
        ),
    }


class LatestQuoteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, symbol):
        stock = get_object_or_404(
            Stock, symbol__iexact=symbol.strip(), is_active=True,
        )
        quote = LatestQuote.objects.select_related("stock").filter(stock=stock).first()
        if quote is not None:
            return Response(LatestQuoteSerializer(quote).data, status=status.HTTP_200_OK)
        archived = archived_quote_payload(stock)
        if archived is not None:
            return Response(archived, status=status.HTTP_200_OK)
        return Response(
            {
                "detail": (
                    f"No stored quote or historical daily price exists for {stock.symbol}. "
                    "This preview has no market-data observations yet. "
                    "Import a validated market snapshot or use the provider refresh command."
                ),
                "symbol": stock.symbol,
                "data_status": "missing_stored_market_data",
            },
            status=status.HTTP_404_NOT_FOUND,
        )
