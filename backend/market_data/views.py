from rest_framework import generics

from .models import HistoricalPrice
from .serializers import HistoricalPriceSerializer


class HistoricalPriceListView(generics.ListAPIView):
    serializer_class = HistoricalPriceSerializer

    def get_queryset(self):
        stock_id = self.request.query_params.get("stock")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        queryset = HistoricalPrice.objects.select_related("stock")

        if stock_id:
            queryset = queryset.filter(stock_id=stock_id)

        if start_date:
            queryset = queryset.filter(date__gte=start_date)

        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by("date")