
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock

from .models import LatestQuote
from .quote_serializers import LatestQuoteSerializer


class LatestQuoteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, symbol):
        stock = get_object_or_404(
            Stock,
            symbol__iexact=symbol.strip(),
            is_active=True,
        )

        try:
            quote = LatestQuote.objects.select_related(
                "stock"
            ).get(stock=stock)

        except LatestQuote.DoesNotExist:
            return Response(
                {
                    "detail": (
                        f"No stored quote exists for {stock.symbol}. "
                        "Run the refresh_latest_quote management command first."
                    ),
                    "symbol": stock.symbol,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LatestQuoteSerializer(quote)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
