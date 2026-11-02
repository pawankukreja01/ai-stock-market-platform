
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import LatestQuote


class LatestQuoteSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(
        source="stock.symbol",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="stock.company_name",
        read_only=True,
    )

    exchange = serializers.CharField(
        source="stock.exchange",
        read_only=True,
    )

    change = serializers.SerializerMethodField()
    change_percent = serializers.SerializerMethodField()
    freshness_status = serializers.SerializerMethodField()
    data_note = serializers.SerializerMethodField()

    class Meta:
        model = LatestQuote

        fields = [
            "id",
            "symbol",
            "company_name",
            "exchange",
            "provider_currency",
            "price",
            "previous_close",
            "change",
            "change_percent",
            "volume",
            "currency",
            "provider",
            "quote_type",
            "source_timestamp",
            "retrieved_at",
            "freshness_status",
            "data_note",
        ]

    def get_change(self, obj):
        if obj.previous_close is None:
            return None

        return format(
            obj.price - obj.previous_close,
            "f",
        )

    def get_change_percent(self, obj):
        if (
            obj.previous_close is None
            or obj.previous_close <= 0
        ):
            return None

        change = obj.price - obj.previous_close

        percentage = (
            change / obj.previous_close * Decimal("100")
        )

        return format(
            percentage.quantize(Decimal("0.01")),
            "f",
        )

    def get_freshness_status(self, obj):
        age = timezone.now() - obj.source_timestamp

        if age < timedelta(minutes=-5):
            return "unknown"

        if age <= timedelta(minutes=30):
            return "recent"

        if age <= timedelta(days=5):
            return "latest_available"

        return "stale"

    def get_data_note(self, obj):
        if obj.quote_type == "daily_close":
            note = (
                "Latest available daily closing price. "
                "Intraday data was unavailable."
            )
        else:
            note = (
                "Latest available intraday one-minute bar from "
                "Yahoo Finance. Real-time delivery is not guaranteed."
            )

        if obj.provider_currency in ("GBp", "GBX"):
            note += (
                " Yahoo Finance supplied prices in pence sterling; "
                "prices have been normalized to GBP."
            )

        return note