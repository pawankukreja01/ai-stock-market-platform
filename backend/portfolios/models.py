from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from stocks.models import Stock


class Portfolio(models.Model):
    # Keep pre-existing rows unassigned until ownership can be confirmed.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="marketpulse_portfolios", null=True, blank=True,
    )
    name = models.CharField(
        max_length=120,
        default="My Portfolio",
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class PortfolioHolding(models.Model):
    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    stock = models.ForeignKey(
        Stock,
        on_delete=models.PROTECT,
        related_name="portfolio_holdings",
    )
    quantity = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[
            MinValueValidator(Decimal("0.000001")),
        ],
    )
    purchase_price = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        validators=[
            MinValueValidator(Decimal("0.0001")),
        ],
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stock__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "stock"],
                name="unique_stock_per_portfolio",
            ),
        ]

    def __str__(self):
        return (
            f"{self.portfolio.name}: "
            f"{self.stock.symbol} x {self.quantity}"
        )

    @property
    def cost_basis(self):
        return self.quantity * self.purchase_price