from django.db import models

from stocks.models import Stock


class HistoricalPrice(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="historical_prices",
    )

    date = models.DateField()

    open_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    high_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    low_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    close_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    adjusted_close = models.DecimalField(
        max_digits=15,
        decimal_places=4,
    )

    volume = models.BigIntegerField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["stock", "date"],
                name="unique_stock_date",
            )
        ]

        ordering = ["-date"]

    def __str__(self):
        return f"{self.stock.symbol} - {self.date}"


class Fundamental(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="fundamentals",
    )

    # --------------------------------------------------
    # Reporting period
    # --------------------------------------------------

    period_end = models.DateField(
        null=True,
        blank=True,
    )

    period_type = models.CharField(
        max_length=20,
        choices=[
            ("annual", "Annual"),
            ("quarterly", "Quarterly"),
        ],
        default="annual",
    )

    # --------------------------------------------------
    # Profitability / income statement
    # --------------------------------------------------

    revenue = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    gross_profit = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    operating_income = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    net_income = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    eps = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Cash flow
    # --------------------------------------------------

    free_cash_flow = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Profitability ratios
    # --------------------------------------------------

    roe = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    roa = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    gross_margin = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    operating_margin = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    profit_margin = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Financial health
    # --------------------------------------------------

    debt_to_equity = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    current_ratio = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Valuation
    # --------------------------------------------------

    pe_ratio = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    forward_pe = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    peg_ratio = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    price_to_sales = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    price_to_book = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Dividends
    # --------------------------------------------------

    dividend_per_share = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    dividend_yield = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        null=True,
        blank=True,
    )

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "stock",
                    "period_end",
                    "period_type",
                ],
                name="unique_stock_fundamental_period",
            )
        ]

        ordering = ["-period_end"]

    def __str__(self):
        return (
            f"{self.stock.symbol} - "
            f"{self.period_type} - "
            f"{self.period_end}"
        )