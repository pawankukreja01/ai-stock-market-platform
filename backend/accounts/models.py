
from django.conf import settings
from django.db import models


def profile_picture_upload_path(instance, filename):
    return f"profile_pictures/user_{instance.user_id}/{filename}"


class UserProfile(models.Model):
    class MarketChoices(models.TextChoices):
        GLOBAL = "global", "Global"
        US = "us", "United States"
        UK = "uk", "United Kingdom"
        PAKISTAN = "pakistan", "Pakistan"

    class RiskChoices(models.TextChoices):
        CONSERVATIVE = "conservative", "Conservative"
        MODERATE = "moderate", "Moderate"
        AGGRESSIVE = "aggressive", "Aggressive"

    class HorizonChoices(models.TextChoices):
        SHORT = "short", "Short-term"
        MEDIUM = "medium", "Medium-term"
        LONG = "long", "Long-term"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    email_verified = models.BooleanField(default=True)

    profile_picture = models.ImageField(
        upload_to=profile_picture_upload_path,
        blank=True,
        null=True,
    )

    preferred_market = models.CharField(
        max_length=20,
        choices=MarketChoices.choices,
        default=MarketChoices.GLOBAL,
    )

    risk_tolerance = models.CharField(
        max_length=20,
        choices=RiskChoices.choices,
        default=RiskChoices.MODERATE,
    )

    investment_horizon = models.CharField(
        max_length=20,
        choices=HorizonChoices.choices,
        default=HorizonChoices.MEDIUM,
    )

    preferred_sectors = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Profile for {self.user.username}"
