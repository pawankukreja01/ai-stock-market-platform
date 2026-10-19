from decimal import Decimal, ROUND_HALF_UP
import math

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from alerts.models import AlertRule, AlertEvent
from market_data.models import HistoricalPrice, NewsArticle


def get_observed_value(rule):
    """Get the latest stored price or average recent news sentiment."""

    if rule.alert_type in {
        AlertRule.PRICE_ABOVE,
        AlertRule.PRICE_BELOW,
    }:
        return (
            HistoricalPrice.objects
            .filter(stock_id=rule.stock_id)
            .order_by("-date")
            .values_list("close_price", flat=True)
            .first()
        )

    scores = list(
        NewsArticle.objects.filter(
            stock_id=rule.stock_id,
            sentiment_analyzed_at__isnull=False,
            sentiment_score__isnull=False,
        )
        .order_by(
            F("published_at").desc(nulls_last=True),
            "-retrieved_at",
        )
        .values_list("sentiment_score", flat=True)[:50]
    )

    valid_scores = []

    for score in scores:
        try:
            numeric_score = float(score)
        except (TypeError, ValueError):
            continue

        if math.isfinite(numeric_score):
            valid_scores.append(Decimal(str(numeric_score)))

    if not valid_scores:
        return None

    average = sum(valid_scores) / Decimal(len(valid_scores))

    return average.quantize(
        Decimal("0.000001"),
        rounding=ROUND_HALF_UP,
    )


def is_condition_met(rule, observed_value):
    """Evaluate a rule using a strict above/below comparison."""

    if rule.alert_type == AlertRule.PRICE_ABOVE:
        return observed_value > rule.threshold

    if rule.alert_type == AlertRule.PRICE_BELOW:
        return observed_value < rule.threshold

    if rule.alert_type == AlertRule.SENTIMENT_ABOVE:
        return observed_value > rule.threshold

    if rule.alert_type == AlertRule.SENTIMENT_BELOW:
        return observed_value < rule.threshold

    return False


def make_alert_message(rule, observed_value):
    """Create a readable description of the trigger."""

    label = rule.get_alert_type_display()
    symbol = rule.stock.symbol

    if rule.alert_type in {
        AlertRule.PRICE_ABOVE,
        AlertRule.PRICE_BELOW,
    }:
        return (
            f"{symbol} latest stored closing price "
            f"(${observed_value:,.2f}) met the rule "
            f"'{label}' at threshold ${rule.threshold:,.2f}."
        )

    return (
        f"{symbol} average recent news sentiment "
        f"({observed_value:.4f}) met the rule '{label}' "
        f"at threshold {rule.threshold:.4f}."
    )


class Command(BaseCommand):
    help = (
        "Evaluate active price and news sentiment alert rules "
        "against stored market data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            help="Evaluate rules for one stock symbol only.",
        )
        parser.add_argument(
            "--rule-id",
            type=int,
            help="Evaluate one alert rule by ID.",
        )

    def handle(self, *args, **options):
        rules = AlertRule.objects.filter(
            is_active=True,
        ).values_list("id", flat=True)

        if options.get("symbol"):
            rules = rules.filter(
                stock__symbol__iexact=options["symbol"].strip()
            )

        if options.get("rule_id"):
            rules = rules.filter(pk=options["rule_id"])

        rule_ids = list(rules.order_by("id"))

        self.stdout.write(
            f"Evaluating {len(rule_ids)} active alert rule(s)..."
        )

        triggered_count = 0
        already_met_count = 0
        reset_count = 0
        no_data_count = 0

        for rule_id in rule_ids:
            with transaction.atomic():
                try:
                    rule = (
                        AlertRule.objects
                        .select_for_update()
                        .select_related("stock")
                        .get(pk=rule_id, is_active=True)
                    )
                except AlertRule.DoesNotExist:
                    continue

                observed_value = get_observed_value(rule)

                if observed_value is None:
                    no_data_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"SKIPPED rule {rule.id} "
                            f"({rule.stock.symbol}): no usable data."
                        )
                    )
                    continue

                was_met = rule.condition_met
                now_met = is_condition_met(rule, observed_value)

                rule.condition_met = now_met
                rule.last_observed_value = observed_value
                rule.last_evaluated_at = timezone.now()

                rule.save(update_fields=[
                    "condition_met",
                    "last_observed_value",
                    "last_evaluated_at",
                    "updated_at",
                ])

                if now_met and not was_met:
                    AlertEvent.objects.create(
                        rule=rule,
                        observed_value=observed_value,
                        message=make_alert_message(
                            rule,
                            observed_value,
                        ),
                    )
                    triggered_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"TRIGGERED rule {rule.id}: "
                            f"{rule.stock.symbol} — "
                            f"{observed_value}"
                        )
                    )

                elif now_met:
                    already_met_count += 1

                    self.stdout.write(
                        f"STILL MET rule {rule.id}: "
                        f"{rule.stock.symbol} — "
                        f"{observed_value}"
                    )

                elif was_met:
                    reset_count += 1

                    self.stdout.write(
                        f"RESET rule {rule.id}: "
                        f"{rule.stock.symbol} no longer meets "
                        "the condition."
                    )

                else:
                    self.stdout.write(
                        f"NOT MET rule {rule.id}: "
                        f"{rule.stock.symbol} — "
                        f"{observed_value}"
                    )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "Alert evaluation complete."
        ))
        self.stdout.write(f"New events triggered: {triggered_count}")
        self.stdout.write(f"Conditions still met: {already_met_count}")
        self.stdout.write(f"Conditions reset: {reset_count}")
        self.stdout.write(f"Rules skipped due to missing data: {no_data_count}")