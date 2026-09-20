from rest_framework import viewsets

from .models import Stock
from .serializers import StockSerializer


class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all().order_by("symbol")
    serializer_class = StockSerializer