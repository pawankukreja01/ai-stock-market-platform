from rest_framework import serializers

from .models import HistoricalPrice, Fundamental


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


class FundamentalSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(
        source="stock.symbol",
        read_only=True,
    )

    company_name = serializers.CharField(
        source="stock.company_name",
        read_only=True,
    )

    sector = serializers.CharField(
        source="stock.sector",
        read_only=True,
    )

    class Meta:
        model = Fundamental

        fields = [
            "id",
            "stock",
            "symbol",
            "company_name",
            "sector",

            "period_end",
            "period_type",

            "revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "eps",

            "free_cash_flow",

            "roe",
            "roa",
            "gross_margin",
            "operating_margin",
            "profit_margin",

            "debt_to_equity",
            "current_ratio",

            "pe_ratio",
            "forward_pe",
            "peg_ratio",
            "price_to_sales",
            "price_to_book",

            "dividend_per_share",
            "dividend_yield",

            "created_at",
            "updated_at",
        ]