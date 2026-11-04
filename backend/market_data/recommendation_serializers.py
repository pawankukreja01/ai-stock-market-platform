
from rest_framework import serializers
from decimal import Decimal


class RecommendationRequestSerializer(serializers.Serializer):
    """Validate the user's investment recommendation request."""

    budget = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    currency = serializers.CharField(
        max_length=3,
        min_length=3,
    )

    risk_tolerance = serializers.ChoiceField(
        choices=("low", "moderate", "high"),
    )

    horizon_months = serializers.IntegerField(
        min_value=1,
        max_value=600,
    )

    market = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=False,
    )

    max_candidates = serializers.IntegerField(
        min_value=1,
        max_value=100,
        default=20,
    )

    allocation_method = serializers.ChoiceField(
        choices=("diversified", "rank_first"),
        default="diversified",
        help_text=(
            "diversified: fixed per-position/sector concentration limits; "
            "rank_first: legacy single-position-heavy paper allocation."
        ),
    )

    def validate_currency(self, value):
        value = value.upper()

        if not value.isalpha():
            raise serializers.ValidationError(
                "Currency must be a three-letter code."
            )

        return value

    def validate_market(self, value):
        return value.strip()
