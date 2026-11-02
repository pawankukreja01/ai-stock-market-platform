from rest_framework import serializers

from .catalog import POPULAR_SYMBOLS, market_for_exchange
from .models import Stock


class StockSerializer(serializers.ModelSerializer):
    market = serializers.SerializerMethodField()
    is_popular = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "id",
            "symbol",
            "company_name",
            "exchange",
            "currency",
            "market",
            "sector",
            "industry",
            "is_active",
            "is_popular",
            "created_at",
            "updated_at",
        ]

    def get_market(self, obj):
        return market_for_exchange(obj.exchange)

    def get_is_popular(self, obj):
        return obj.symbol.upper() in POPULAR_SYMBOLS
