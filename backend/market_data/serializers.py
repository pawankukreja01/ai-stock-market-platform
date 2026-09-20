from rest_framework import serializers

from .models import HistoricalPrice


class HistoricalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalPrice
        fields = [
            "id",
            "stock",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "adjusted_close",
            "volume",
        ]