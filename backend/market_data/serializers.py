from rest_framework import serializers

from .models import (
    HistoricalPrice,
    Fundamental,
    NewsArticle,
)


# ============================================================
# HISTORICAL PRICES
# ============================================================

class HistoricalPriceSerializer(
    serializers.ModelSerializer
):
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
            "provider_currency",
            "storage_currency",
            "is_ohlc_valid",
            "is_volume_valid",
            "quality_flags",
        ]


# ============================================================
# FUNDAMENTALS
# ============================================================

class FundamentalSerializer(
    serializers.ModelSerializer
):
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


# ============================================================
# NEWS ARTICLES
# ============================================================


class NewsArticleSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(
        source="stock.symbol",
        read_only=True,
    )
    company_name = serializers.CharField(
        source="stock.company_name",
        read_only=True,
    )

    class Meta:
        model = NewsArticle
        fields = [
            "id",
            "symbol",
            "company_name",
            "source_name",
            "source_id",
            "title",
            "summary",
            "url",
            "publisher",
            "published_at",
            "thumbnail_url",
            "sentiment_label",
            "sentiment_score",
            "sentiment_positive_prob",
            "sentiment_neutral_prob",
            "sentiment_negative_prob",
            "sentiment_model",
            "sentiment_analyzed_at",
            "retrieved_at",
            "created_at",
        ]
