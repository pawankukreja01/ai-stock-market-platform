from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .catalog import MARKET_EXCHANGES, POPULAR_SYMBOLS
from .models import Stock
from .serializers import StockSerializer


class StockCatalogPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "page": self.page.number,
                "page_size": self.page.paginator.per_page,
                "total_pages": self.page.paginator.num_pages,
                "results": data,
            }
        )


class StockViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Stock.objects.all().order_by("symbol")
    serializer_class = StockSerializer
    pagination_class = StockCatalogPagination

    def _invalid_market_response(self):
        market = self.request.query_params.get("market", "").strip().upper()
        if market and market not in MARKET_EXCHANGES:
            return Response(
                {"error": "market must be 'US' or 'UK'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def get_queryset(self):
        queryset = super().get_queryset()

        # Public catalogue and detail endpoints expose only active stocks.
        if self.action not in {"list", "popular"}:
            return queryset.filter(is_active=True)

        queryset = queryset.filter(is_active=True)
        params = self.request.query_params

        search = params.get("search", params.get("q", "")).strip()
        if search:
            queryset = queryset.filter(
                Q(symbol__icontains=search)
                | Q(company_name__icontains=search)
                | Q(sector__icontains=search)
                | Q(industry__icontains=search)
            )

        market = params.get("market", "").strip().upper()
        if market:
            queryset = queryset.filter(exchange__in=MARKET_EXCHANGES[market])

        exchange = params.get("exchange", "").strip()
        if exchange:
            queryset = queryset.filter(exchange__iexact=exchange)

        sectors = [
          item.strip()
          for item in params.get("sector", "").split(",")
          if item.strip()
        ]

        if sectors:
          sector_query = Q()
          for item in sectors:
            sector_query |= (
                Q(sector__icontains=item)
                | Q(industry__icontains=item)
            )

          queryset = queryset.filter(sector_query)

        return queryset.order_by("symbol")

    def _collection_response(self, queryset):
        # Preserve the original list-of-records response unless pagination
        # is explicitly requested by the caller.
        wants_pagination = (
            "page" in self.request.query_params
            or "page_size" in self.request.query_params
        )

        if wants_pagination:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        invalid_market = self._invalid_market_response()
        if invalid_market:
            return invalid_market

        queryset = self.filter_queryset(self.get_queryset())
        return self._collection_response(queryset)

    @action(detail=False, methods=["get"], url_path="popular")
    def popular(self, request):
        """Return the curated discovery shortlist; this is not investment advice."""
        invalid_market = self._invalid_market_response()
        if invalid_market:
            return invalid_market

        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(symbol__in=POPULAR_SYMBOLS)
        return self._collection_response(queryset)
