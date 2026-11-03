"""Read-only daily research health report for personal MarketPulse monitoring.

The report is about source freshness and coverage, NOT prediction skill.
No requests to providers, no model fitting, no DB writes and no alert events.
"""

import json
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Max, Q
from django.utils import timezone

from stocks.models import Stock


def research_health_status(
    *, now, latest_price_date, price_count, invalid_price_count,
    latest_quote_time, quarterly_count, annual_count,
    min_history, max_history_age_days, max_quote_age_minutes,
):
    """Pure status calculation; provider timestamps are authoritative."""
    flags = []
    if price_count < min_history:
        flags.append("insufficient_history")
    if latest_price_date is None:
        flags.append("missing_price_history")
    else:
        price_age = (now.date() - latest_price_date).days
        if price_age < 0:
            flags.append("future_price_date")
        elif price_age > max_history_age_days:
            flags.append("stale_price_history")

    if invalid_price_count:
        flags.append("invalid_ohlc_rows")

    if latest_quote_time is None:
        flags.append("missing_quote")
        quote_age_minutes = None
    else:
        try:
            quote_age_minutes = round(
                (now - latest_quote_time).total_seconds() / 60.0, 1
            )
        except TypeError:
            quote_age_minutes = None
        if quote_age_minutes is None or quote_age_minutes < -5:
            flags.append("invalid_quote_timestamp")
        elif quote_age_minutes > max_quote_age_minutes:
            flags.append("stale_quote")

    # Missing financial statements are availability warnings rather
    # than fabricated zero values or proof of provider failure.
    gaps = []
    if annual_count == 0:
        gaps.append("annual_fundamentals_unavailable")
    if quarterly_count == 0:
        gaps.append("quarterly_fundamentals_unavailable")

    return {
        "status": "attention" if flags else "ok",
        "flags": flags,
        "availability_gaps": gaps,
        "price_observations": int(price_count),
        "invalid_ohlc_rows": int(invalid_price_count),
        "latest_price_date": (
            latest_price_date.isoformat() if latest_price_date else None
        ),
        "quote_source_age_minutes": quote_age_minutes,
    }


class Command(BaseCommand):
    help = (
        "Read-only stock research health audit. Prints a JSON report, "
        "optionally saves a new JSON file; no provider calls or database changes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols", nargs="+",
            help="Optional explicit subset; defaults to all active stocks.",
        )
        parser.add_argument(
            "--min-history", type=int, default=300,
        )
        parser.add_argument(
            "--max-history-age-days", type=int, default=7,
        )
        parser.add_argument(
            "--max-quote-age-minutes", type=int, default=30,
        )
        parser.add_argument(
            "--strict", action="store_true",
            help="Exit with failure if any selected stock needs attention.",
        )
        parser.add_argument(
            "--output", type=str,
            help="Optional new JSON report path; refuses to overwrite existing.",
        )

    def handle(self, *args, **options):
        if (
            options["min_history"] < 1
            or options["max_history_age_days"] < 0
            or options["max_quote_age_minutes"] < 1
        ):
            raise CommandError("Audit thresholds must be positive or nonnegative.")

        symbols = options.get("symbols")
        tickers = None
        if symbols:
            tickers = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
            if not tickers or len(tickers) > 200:
                raise CommandError("Supply between 1 and 200 stock symbols.")

        queryset = Stock.objects.filter(is_active=True)
        if tickers:
            queryset = queryset.filter(symbol__in=tickers)
        queryset = queryset.annotate(
            price_count=Count(
                "historical_prices",
                filter=Q(historical_prices__date__lte=timezone.localdate()),
                distinct=True,
            ),
            invalid_price_count=Count(
                "historical_prices",
                filter=Q(
                    historical_prices__date__lte=timezone.localdate(),
                    historical_prices__is_ohlc_valid=False,
                ),
                distinct=True,
            ),
            latest_price=Max("historical_prices__date"),
            annual_count=Count(
                "fundamentals",
                filter=Q(fundamentals__period_type="annual"),
                distinct=True,
            ),
            quarterly_count=Count(
                "fundamentals",
                filter=Q(fundamentals__period_type="quarterly"),
                distinct=True,
            ),
            latest_news=Max("news_articles__published_at"),
        ).select_related("latest_quote").order_by("symbol")

        if tickers and queryset.count() != len(tickers):
            raise CommandError("Unknown or inactive symbols in research health request.")

        now = timezone.now()
        rows = []
        for stock in queryset.iterator(chunk_size=100):
            try:
                source_time = stock.latest_quote.source_timestamp
            except (AttributeError, Stock.latest_quote.RelatedObjectDoesNotExist):
                source_time = None

            details = research_health_status(
                now=now,
                latest_price_date=stock.latest_price,
                price_count=stock.price_count,
                invalid_price_count=stock.invalid_price_count,
                latest_quote_time=source_time,
                annual_count=stock.annual_count,
                quarterly_count=stock.quarterly_count,
                min_history=options["min_history"],
                max_history_age_days=options["max_history_age_days"],
                max_quote_age_minutes=options["max_quote_age_minutes"],
            )
            details.update({
                "symbol": stock.symbol,
                "exchange": stock.exchange,
                "annual_statement_count": stock.annual_count,
                "quarterly_statement_count": stock.quarterly_count,
                "latest_news_date": (
                    stock.latest_news.isoformat() if stock.latest_news else None
                ),
                "quote_source_timestamp": (
                    source_time.isoformat() if source_time else None
                ),
            })
            rows.append(details)

        flagged = sum(item["status"] != "ok" for item in rows)
        report = {
            "as_of_utc": now.isoformat(),
            "source": "stored MarketPulse database only",
            "read_only": True,
            "purpose": "data availability and freshness; not forecast skill",
            "thresholds": {
                "min_history": options["min_history"],
                "max_history_age_days": options["max_history_age_days"],
                "max_quote_age_minutes": options["max_quote_age_minutes"],
            },
            "summary": {
                "stocks": len(rows),
                "stocks_needing_attention": flagged,
                "stocks_with_no_annual_statements": sum(
                    not item["annual_statement_count"] for item in rows
                ),
                "stocks_with_no_quarterly_statements": sum(
                    not item["quarterly_statement_count"] for item in rows
                ),
            },
            "stocks": rows,
        }
        serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if options["output"]:
            dest = Path(options["output"]).expanduser().resolve()
            if dest.exists():
                raise CommandError(f"Refusing to overwrite health report: {dest}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(serialized, encoding="utf-8")
            self.stdout.write(f"Health report saved: {dest}")
        else:
            self.stdout.write(serialized)

        if options["strict"] and (not rows or flagged):
            raise CommandError(
                f"Research health failed: {flagged}/{len(rows)} stocks need attention."
            )
