
from django.db import models

from stocks.models import Stock


class HistoricalPrice(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="historical_prices",
    )

    date = models.DateField()

    # OHLC values can be NULL when the provider does not supply
    # a usable component. The closing price remains mandatory.
    open_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
    )
    high_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
    )
    low_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
    )

    close_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    adjusted_close = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    # Invalid or unavailable volume is represented as NULL.
    volume = models.BigIntegerField(
        null=True,
        blank=True,
    )

    # Currency provenance.
    provider_currency = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Original currency denomination supplied by the provider.",
    )

    storage_currency = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Currency denomination used for stored monetary prices.",
    )

    # Independent data-quality dimensions.
    is_ohlc_valid = models.BooleanField(default=True)
    is_volume_valid = models.BooleanField(default=True)

    # JSON list of quality issues, for example HIGH_BELOW_OPEN.
    quality_flags = models.JSONField(
        default=list,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "date"],
                name="unique_stock_date",
            ),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"


class Fundamental(models.Model):
    PERIOD_CHOICES = [
        ("annual", "Annual"),
        ("quarterly", "Quarterly"),
    ]

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="fundamentals",
    )
    period_end = models.DateField(null=True, blank=True)
    period_type = models.CharField(
        max_length=10,
        choices=PERIOD_CHOICES,
        default="annual",
    )

    revenue = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    gross_profit = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    operating_income = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    net_income = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    eps = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    free_cash_flow = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    roe = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    roa = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    gross_margin = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    operating_margin = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    profit_margin = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    debt_to_equity = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    current_ratio = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    pe_ratio = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    forward_pe = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    peg_ratio = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    price_to_sales = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    price_to_book = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    dividend_per_share = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    dividend_yield = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )

    # Preserve nullable timestamp fields for existing records.
    created_at = models.DateTimeField(
        auto_now_add=True, null=True, blank=True
    )
    updated_at = models.DateTimeField(
        auto_now=True, null=True, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "period_end", "period_type"],
                name="unique_stock_fundamental_period",
            ),
        ]
        ordering = ["-period_end"]

    def __str__(self):
        return (
            f"{self.stock.symbol} - "
            f"{self.period_type} - {self.period_end}"
        )


class NewsArticle(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="news_articles",
    )
    source_name = models.CharField(
        max_length=100, default="Yahoo Finance"
    )
    source_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)
    url = models.URLField(max_length=2048)
    publisher = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=2048, blank=True)

    # Sentiment analysis fields
    sentiment_label = models.CharField(
        max_length=10,
        choices=[
            ("positive", "Positive"),
            ("neutral", "Neutral"),
            ("negative", "Negative"),
        ],
        blank=True,
        default="",
    )
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_positive_prob = models.FloatField(null=True, blank=True)
    sentiment_neutral_prob = models.FloatField(null=True, blank=True)
    sentiment_negative_prob = models.FloatField(null=True, blank=True)
    sentiment_model = models.CharField(
        max_length=100, blank=True, default=""
    )
    sentiment_analyzed_at = models.DateTimeField(
        null=True, blank=True
    )

    retrieved_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "url"],
                name="unique_stock_news_url",
            ),
        ]
        ordering = ["-published_at", "-retrieved_at"]

    def __str__(self):
        return f"{self.stock.symbol} - {self.title}"


class LatestQuote(models.Model):
    QUOTE_TYPE_CHOICES = [
        ("intraday_1m", "Intraday 1-minute bar"),
        ("daily_close", "Latest daily close"),
    ]

    stock = models.OneToOneField(
        Stock,
        on_delete=models.CASCADE,
        related_name="latest_quote",
    )

    price = models.DecimalField(max_digits=20, decimal_places=6)

    previous_close = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    volume = models.BigIntegerField(null=True, blank=True)

    currency = models.CharField(
        max_length=3,
        null=True,
        blank=True,
    )

    provider_currency = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Original currency denomination reported by the provider.",
    )

    provider = models.CharField(
        max_length=50,
        default="yfinance",
    )

    quote_type = models.CharField(
        max_length=20,
        choices=QUOTE_TYPE_CHOICES,
    )

    source_timestamp = models.DateTimeField()
    retrieved_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-source_timestamp"]
        verbose_name = "Latest stock quote"
        verbose_name_plural = "Latest stock quotes"

    def __str__(self):
        return (
            f"{self.stock.symbol} - "
            f"{self.price} {self.currency or ''}"
        )
