"""Read-only operational audit of stored market-data coverage.

This is a smoke test of DATA AVAILABILITY, not of prediction quality or
a certification of investment readiness.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Max, Q
from django.utils import timezone

from stocks.models import Stock


def classify_price_history(*, count, latest_date, today, minimum, max_age):
    """Pure threshold helper for both local diagnostics and unit tests."""
    problems = []
    if count < minimum:
        problems.append(f"only {count} price rows (minimum {minimum})")
    if latest_date is None:
        problems.append("no stored price date")
    else:
        age = (today - latest_date).days
        if age < 0:
            problems.append("last price date is in the future")
        elif age > max_age:
            problems.append(f"last price is {age} calendar days old (limit {max_age})")
    return problems


class Command(BaseCommand):
    help = "Read-only stock data-readiness report; never downloads or changes data."

    def add_arguments(self, parser):
        parser.add_argument("--min-history", type=int, default=300)
        parser.add_argument("--max-price-age-days", type=int, default=7)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--strict", action="store_true",
                            help="Exit nonzero if any active stocks need attention.")

    def handle(self, *args, **options):
        minimum = options["min_history"]
        max_age = options["max_price_age_days"]
        limit = options["limit"]
        if minimum < 1 or max_age < 0 or limit < 0:
            raise CommandError("Invalid audit thresholds.")

        today = timezone.localdate()
        stocks = (
            Stock.objects.filter(is_active=True)
            .annotate(
                price_rows=Count(
                    "historical_prices",
                    filter=Q(historical_prices__date__lte=today,
                             historical_prices__close_price__gt=0),
                    distinct=True,
                ),
                latest_price=Max(
                    "historical_prices__date",
                    filter=Q(historical_prices__date__lte=today,
                             historical_prices__close_price__gt=0),
                ),
                fundamental_rows=Count("fundamentals", distinct=True),
                news_rows=Count("news_articles", distinct=True),
            )
            .order_by("symbol")
        )

        total = 0
        ready = 0
        missing_fundamentals = 0
        missing_news = 0
        flagged = []

        for stock in stocks.iterator():
            total += 1
            problems = classify_price_history(
                count=stock.price_rows,
                latest_date=stock.latest_price,
                today=today,
                minimum=minimum,
                max_age=max_age,
            )
            if not stock.fundamental_rows:
                missing_fundamentals += 1
            if not stock.news_rows:
                missing_news += 1
            if problems:
                flagged.append((stock.symbol, "; ".join(problems)))
            else:
                ready += 1

        self.stdout.write(f"MarketPulse data-readiness audit at {today}")
        self.stdout.write(f"Active stocks: {total}")
        self.stdout.write(f"History coverage and recency gate passed: {ready}/{total}")
        self.stdout.write(f"Stocks without fundamentals: {missing_fundamentals}")
        self.stdout.write(f"Stocks without news: {missing_news}")
        self.stdout.write(
            "Data availability alone does not imply predictable returns, "
            "accurate market data, or production readiness."
        )
        for symbol, problem in flagged[:limit]:
            self.stdout.write(f"  {symbol}: {problem}")
        if len(flagged) > limit:
            self.stdout.write(f"  ...and {len(flagged) - limit} more.")

        if options["strict"] and (total == 0 or flagged):
            raise CommandError(
                f"Data audit failed: {len(flagged)} stocks need attention "
                f"out of {total} active."
            )
