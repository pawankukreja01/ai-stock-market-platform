from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from stocks.models import Stock


class AlertRule(models.Model):
    # Legacy records are hidden until an administrator establishes ownership.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="marketpulse_alert_rules", null=True, blank=True,
    )

    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    SENTIMENT_ABOVE = "sentiment_above"
    SENTIMENT_BELOW = "sentiment_below"

    ALERT_TYPE_CHOICES = [
        (PRICE_ABOVE, "Price above threshold"),
        (PRICE_BELOW, "Price below threshold"),
        (SENTIMENT_ABOVE, "Sentiment above threshold"),
        (SENTIMENT_BELOW, "Sentiment below threshold"),
    ]

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="alert_rules",
    )

    name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    alert_type = models.CharField(
        max_length=30,
        choices=ALERT_TYPE_CHOICES,
    )

    threshold = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    is_active = models.BooleanField(default=True)

    # Tracks whether the condition was already met during
    # the previous evaluation. This prevents repeated events
    # while the condition stays true.
    condition_met = models.BooleanField(default=False)

    last_observed_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True,
    )

    last_evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["is_active", "alert_type"],
                name="alert_active_type_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.stock.symbol}: "
            f"{self.get_alert_type_display()} "
            f"{self.threshold}"
        )

    def clean(self):
        super().clean()

        if self.alert_type in {
            self.SENTIMENT_ABOVE,
            self.SENTIMENT_BELOW,
        }:
            if not DecimalRange.contains(self.threshold):
                from django.core.exceptions import ValidationError

                raise ValidationError({
                    "threshold": (
                        "Sentiment thresholds must be between -1 and 1."
                    )
                })

        elif self.threshold <= 0:
            from django.core.exceptions import ValidationError

            raise ValidationError({
                "threshold": (
                    "Price thresholds must be greater than zero."
                )
            })


class DecimalRange:
    """Small helper for checking supported sentiment thresholds."""

    @staticmethod
    def contains(value):
        return -1 <= value <= 1


class AlertEvent(models.Model):
    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name="events",
    )

    observed_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
    )

    message = models.CharField(max_length=500)

    triggered_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(
                fields=["is_read", "-triggered_at"],
                name="alert_event_read_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.rule.stock.symbol} alert "
            f"triggered at {self.triggered_at}"
        )