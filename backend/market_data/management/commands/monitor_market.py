"""Opt-in personal research monitor using existing yfinance quote ingestion.

This process is deliberately NOT started by Django, and it must not run
against the user's protected original PostgreSQL database. Use an explicitly
selected development database and run it in a separate terminal.
"""

from datetime import timedelta
import os
from decimal import Decimal, InvalidOperation
import time

from django.core.management import call_command
from django.db import connection
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from market_data.quote_service import (
    fetch_latest_quote, QuoteDataUnavailable, QuoteProviderRateLimited,
)
from stocks.models import Stock


DEFAULT_INTERVAL_SECONDS = 300
DEFAULT_MAX_QUOTE_AGE_MINUTES = 30
MAX_WATCHED_STOCKS = 15


def quote_is_fresh_for_alerts(quote, *, now, max_age_minutes):
    """Only act on valid, recent *provider timestamps*, not retrieval time.

    An unchanged quote re-fetched from a closed market must never appear
    fresh merely because it was fetched by the monitoring process.
    """
    timestamp = getattr(quote, "source_timestamp", None)
    price = getattr(quote, "price", None)
    if timestamp is None or price is None or max_age_minutes <= 0:
        return False

    try:
        valid_price = Decimal(str(price)) > 0
    except (InvalidOperation, ValueError, TypeError):
        return False

    if not valid_price:
        return False

    try:
        age = now - timestamp
    except TypeError:
        return False

    return timedelta(minutes=-5) <= age <= timedelta(minutes=max_age_minutes)


class Command(BaseCommand):
    help = (
        "Refresh stored yfinance quotes and evaluate price alerts for an "
        "explicit personal watchlist. Run --continuous to repeat; "
        "this does not provide guaranteed exchange-real-time data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols", nargs="+", required=True,
            help="Explicit personal watchlist, e.g. AAPL MSFT NVDA.",
        )
        parser.add_argument(
            "--continuous", action="store_true",
            help="Repeat until Ctrl+C instead of performing just one cycle.",
        )
        parser.add_argument(
            "--interval-seconds", type=int, default=DEFAULT_INTERVAL_SECONDS,
            help="Delay between cycles, minimum 60 seconds (default: 300).",
        )
        parser.add_argument(
            "--delay-seconds", type=float, default=1,
            help="Delay between stock fetches, minimum 1 second.",
        )
        parser.add_argument(
            "--timeout", type=float, default=15,
            help="Provider timeout in seconds (default: 15).",
        )
        parser.add_argument(
            "--max-quote-age-minutes", type=int,
            default=DEFAULT_MAX_QUOTE_AGE_MINUTES,
            help="Max source timestamp age for price alert evaluation (default: 30).",
        )

    def handle(self, *args, **options):
        # Fail closed: the opt-in monitor may update quotes and alert state.
        # Explicitly select a development DB so a missing environment
        # override cannot silently target the preserved original database.
        explicit_db_name = os.environ.get("DB_NAME", "").strip()
        configured_name = connection.settings_dict["NAME"]
        if (
            not explicit_db_name
            or explicit_db_name != configured_name
            or configured_name == "ai_stock_market"
        ):
            raise CommandError(
                "Monitoring requires explicit DB_NAME for the intended "
                "non-original database. The original ai_stock_market "
                "database is protected."
            )

        symbols = list(dict.fromkeys(
            text.strip().upper() for text in options["symbols"] if text.strip()
        ))
        if not 1 <= len(symbols) <= MAX_WATCHED_STOCKS:
            raise CommandError("Select between 1 and 15 symbols.")
        if options["interval_seconds"] < 60:
            raise CommandError("--interval-seconds must be at least 60.")
        if options["delay_seconds"] < 1:
            raise CommandError("--delay-seconds must be at least 1.")
        if options["timeout"] <= 0:
            raise CommandError("--timeout must be positive.")
        if not 1 <= options["max_quote_age_minutes"] <= 120:
            raise CommandError("--max-quote-age-minutes must be between 1 and 120.")

        stocks = list(
            Stock.objects.filter(symbol__in=symbols, is_active=True)
            .order_by("symbol")
        )
        if len(stocks) != len(symbols):
            found = {stock.symbol for stock in stocks}
            missing = ", ".join(symbol for symbol in symbols if symbol not in found)
            raise CommandError(f"Unknown or inactive watchlist symbol(s): {missing}")

        self.stdout.write(
            "MarketPulse personal quote monitor: "
            + ", ".join(stock.symbol for stock in stocks)
        )
        self.stdout.write(
            "Provider: yfinance; stored quotes may be delayed. "
            "Price alerts only; news sentiment rules are unchanged."
        )
        if options["continuous"]:
            self.stdout.write(
                f"Repeating approximately every {options['interval_seconds']} "
                "seconds after each cycle. Press Ctrl+C to stop."
            )

        cycle = 0
        try:
            while True:
                cycle += 1
                failed = 0
                skipped = 0
                evaluated = 0
                self.stdout.write(
                    f"Cycle {cycle} started at {timezone.now().isoformat()}"
                )

                rate_limited = False
                for index, stock in enumerate(stocks):
                    if index:
                        time.sleep(options["delay_seconds"])
                    try:
                        quote = fetch_latest_quote(
                            stock, timeout=options["timeout"]
                        )
                    except QuoteProviderRateLimited as exc:
                        failed += 1
                        rate_limited = True
                        self.stderr.write(
                            f"{stock.symbol}: Yahoo rate limit detected. "
                            "Stopping all quote requests this cycle; "
                            "existing stored quotes were not overwritten."
                        )
                        break
                    except QuoteDataUnavailable as exc:
                        failed += 1
                        self.stderr.write(
                            f"{stock.symbol}: provider quote unavailable: {exc}"
                        )
                        continue
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(
                            f"{stock.symbol}: quote refresh failed "
                            f"({type(exc).__name__}): {exc}"
                        )
                        continue

                    if not quote_is_fresh_for_alerts(
                        quote,
                        now=timezone.now(),
                        max_age_minutes=options["max_quote_age_minutes"],
                    ):
                        skipped += 1
                        self.stdout.write(
                            f"{stock.symbol}: source {quote.source_timestamp} "
                            "is old or invalid; price alert evaluation skipped."
                        )
                        continue

                    # Existing rule condition_met state prevents repeated
                    # notifications while the same condition stays true.
                    try:
                        call_command(
                            "evaluate_alerts",
                            symbol=stock.symbol,
                            price_only=True,
                            latest_prices=True,
                            max_quote_age_minutes=options["max_quote_age_minutes"],
                            stdout=self.stdout,
                            stderr=self.stderr,
                        )
                        evaluated += 1
                        self.stdout.write(
                            f"{stock.symbol}: stored {quote.price} {quote.currency or ''} "
                            f"as of {quote.source_timestamp}"
                        )
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(
                            f"{stock.symbol}: price-alert evaluation failed "
                            f"({type(exc).__name__}): {exc}"
                        )

                if rate_limited:
                    self.stdout.write(
                        "Monitoring stopped to avoid further requests while "
                        "the provider is rate limiting. Recheck provider "
                        "availability before explicitly restarting."
                    )
                    if not options["continuous"]:
                        raise CommandError(
                            "Yahoo provider rate limited; remaining stocks skipped."
                        )
                    break

                self.stdout.write(
                    f"Cycle {cycle} finished: {evaluated} symbols evaluated, "
                    f"{skipped} stale/invalid, {failed} failed."
                )

                if not options["continuous"]:
                    if failed:
                        raise CommandError(
                            f"{failed} quote refresh or alert evaluation failure(s)."
                        )
                    break

                time.sleep(options["interval_seconds"])
        except KeyboardInterrupt:
            self.stdout.write("MarketPulse personal monitor stopped.")
