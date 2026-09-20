from django.db import models
from stocks.models import Stock


class HistoricalPrice(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="historical_prices",
    )
    date = models.DateField()

    open_price = models.DecimalField(max_digits=15, decimal_places=4)
    high_price = models.DecimalField(max_digits=15, decimal_places=4)
    low_price = models.DecimalField(max_digits=15, decimal_places=4)
    close_price = models.DecimalField(max_digits=15, decimal_places=4)
    adjusted_close = models.DecimalField(max_digits=15, decimal_places=4)

    volume = models.BigIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

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