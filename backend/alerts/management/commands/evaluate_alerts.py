from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
import math

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from alerts.models import AlertRule, AlertEvent
from market_data.models import HistoricalPrice, NewsArticle, LatestQuote


def get_observed_value(rule, *, use_latest_quote=False, max_quote_age_minutes=30):
    """Read stored market values; never fetch network data while evaluating rules.

    The opt-in latest-quote mode deliberately has NO historical-price fallback:
    stale quotes must not cause notifications for an old price level.
    """
    if rule.alert_type in {
        AlertRule.PRICE_ABOVE,
        AlertRule.PRICE_BELOW,
    }:
        if use_latest_quote:
            now = timezone.now()
            return (
                LatestQuote.objects.filter(
                    stock_id=rule.stock_id,
                    price__gt=0,
                    source_timestamp__gte=now - timedelta(minutes=max_quote_age_minutes),
                    source_timestamp__lte=now + timedelta(minutes=5),
                )
                .values_list("price", flat=True)
                .first()
            )
        return (
            HistoricalPrice.objects
            .filter(
                stock_id=rule.stock_id,
                close_price__gt=0,
            )
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


def make_alert_message(rule, observed_value, *, use_latest_quote=False):
    """Describe the source without claiming exchange-verified real-time data."""

    label = rule.get_alert_type_display()
    symbol = rule.stock.symbol

    if rule.alert_type in {
        AlertRule.PRICE_ABOVE,
        AlertRule.PRICE_BELOW,
    }:
        source = (
            "latest available stored quote" if use_latest_quote
            else "latest stored closing price"
        )
        currency = rule.stock.currency or ""
        return (
            f"{symbol} {source} "
            f"({observed_value:,.2f} {currency}) met the rule "
            f"'{label}' at threshold {rule.threshold:,.2f} {currency}."
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
        parser.add_argument(
            "--latest-prices",
            action="store_true",
            help="Use fresh stored LatestQuote prices with no historical fallback.",
        )
        parser.add_argument(
            "--price-only",
            action="store_true",
            help="Evaluate only price rules; leave news sentiment rules unchanged.",
        )
        parser.add_argument(
            "--max-quote-age-minutes",
            type=int,
            default=30,
            help="Maximum provider timestamp age for --latest-prices (default: 30).",
        )

    def handle(self, *args, **options):
        if options["max_quote_age_minutes"] < 1:
            raise CommandError("--max-quote-age-minutes must be positive.")
        rules = AlertRule.objects.filter(
            is_active=True,
        )
        if options["price_only"]:
            rules = rules.filter(alert_type__in=[
                AlertRule.PRICE_ABOVE, AlertRule.PRICE_BELOW,
            ])
        rules = rules.values_list("id", flat=True)

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

                observed_value = get_observed_value(
                    rule,
                    use_latest_quote=options["latest_prices"],
                    max_quote_age_minutes=options["max_quote_age_minutes"],
                )

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
                            use_latest_quote=options["latest_prices"],
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