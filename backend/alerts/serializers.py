from rest_framework import serializers

from stocks.models import Stock
from .models import AlertRule, AlertEvent


class AlertRuleSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.SlugRelatedField(
        source="stock",
        slug_field="symbol",
        queryset=Stock.objects.filter(is_active=True),
    )
    company_name = serializers.CharField(
        source="stock.company_name",
        read_only=True,
    )

    class Meta:
        model = AlertRule
        fields = [
            "id",
            "stock_symbol",
            "company_name",
            "name",
            "alert_type",
            "threshold",
            "is_active",
            "condition_met",
            "last_observed_value",
            "last_evaluated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company_name",
            "condition_met",
            "last_observed_value",
            "last_evaluated_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        alert_type = attrs.get(
            "alert_type",
            getattr(self.instance, "alert_type", None),
        )
        threshold = attrs.get(
            "threshold",
            getattr(self.instance, "threshold", None),
        )

        if alert_type is None or threshold is None:
            return attrs

        if alert_type in {
            AlertRule.SENTIMENT_ABOVE,
            AlertRule.SENTIMENT_BELOW,
        }:
            if threshold < -1 or threshold > 1:
                raise serializers.ValidationError({
                    "threshold": (
                        "Sentiment thresholds must be between -1 and 1."
                    )
                })
        elif threshold <= 0:
            raise serializers.ValidationError({
                "threshold": (
                    "Price thresholds must be greater than zero."
                )
            })

        return attrs


class AlertEventSerializer(serializers.ModelSerializer):
    stock_symbol = serializers.CharField(
        source="rule.stock.symbol",
        read_only=True,
    )
    rule_name = serializers.CharField(
        source="rule.name",
        read_only=True,
    )
    alert_type = serializers.CharField(
        source="rule.alert_type",
        read_only=True,
    )
    alert_type_label = serializers.CharField(
        source="rule.get_alert_type_display",
        read_only=True,
    )
    threshold = serializers.DecimalField(
        source="rule.threshold",
        max_digits=20,
        decimal_places=6,
        read_only=True,
    )

    class Meta:
        model = AlertEvent
        fields = [
            "id",
            "rule",
            "stock_symbol",
            "rule_name",
            "alert_type",
            "alert_type_label",
            "threshold",
            "observed_value",
            "message",
            "triggered_at",
            "is_read",
        ]
        read_only_fields = fields