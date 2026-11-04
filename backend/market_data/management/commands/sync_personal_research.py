"""Explicit, bounded, one-shot yfinance refresh for personal stock research.

The default invocation is a read-only preview. The --execute option allows
ingestion into ONLY the explicitly named restored test database. This command
never places trades and does not automatically schedule itself.
"""

import os
import time

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from stocks.models import Stock
from market_data.provider_errors import is_provider_rate_limit


REQUIRED_TEST_DB = "marketpulse_restored_test"
MAX_SYMBOLS = 10
ALLOWED_PERIODS = ("1mo", "3mo", "6mo", "1y", "2y", "5y", "10y")


def verify_safe_database(env_db_name, actual_db_name):
    """Require explicit access to only the known restored test database."""
    if env_db_name != REQUIRED_TEST_DB or actual_db_name != REQUIRED_TEST_DB:
        raise CommandError(
            f"Research sync requires DB_NAME={REQUIRED_TEST_DB}; "
            "it refuses to modify the protected original database "
            "ai_stock_market or any other database."
        )


class Command(BaseCommand):
    help = (
        "Preview or execute a bounded one-shot yfinance refresh of historical "
        "OHLC data; optional news, sentiment and fundamentals. Uses only the "
        "explicit restored test database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols", nargs="+", required=True,
            help="Explicit watchlist, e.g. AAPL MSFT NVDA. Max 10.",
        )
        parser.add_argument(
            "--execute", action="store_true",
            help="Actually call ingestion steps. Default only previews operations.",
        )
        parser.add_argument(
            "--period", choices=ALLOWED_PERIODS, default="1y",
            help="yfinance history window to update, default 1y.",
        )
        parser.add_argument(
            "--include-news", action="store_true",
            help="Also fetch latest available Yahoo Finance articles.",
        )
        parser.add_argument(
            "--include-sentiment", action="store_true",
            help="Also analyze the newly fetched articles with FinBERT.",
        )
        parser.add_argument(
            "--include-fundamentals", action="store_true",
            help="Also request financial statements and fundamental metrics.",
        )
        parser.add_argument(
            "--news-limit", type=int, default=20,
            help="Max news articles per symbol (default 20, maximum 50).",
        )
        parser.add_argument(
            "--sentiment-limit", type=int, default=100,
            help="Max sentiment articles per symbol (default 100, maximum 500).",
        )
        parser.add_argument(
            "--timeout", type=float, default=30.0,
            help="History provider request timeout (default 30s).",
        )
        parser.add_argument(
            "--delay-seconds", type=float, default=2.0,
            help="Minimum 1-second delay between tickers (default 2s).",
        )

    def handle(self, *args, **opts):
        verify_safe_database(
            os.environ.get("DB_NAME", "").strip(),
            str(connection.settings_dict["NAME"]),
        )
        if opts["include_sentiment"] and not opts["include_news"]:
            raise CommandError("--include-sentiment requires --include-news.")
        if not 1 <= opts["news_limit"] <= 50:
            raise CommandError("--news-limit must be between 1 and 50.")
        if not 1 <= opts["sentiment_limit"] <= 500:
            raise CommandError("--sentiment-limit must be between 1 and 500.")
        if opts["timeout"] <= 0 or opts["delay_seconds"] < 1:
            raise CommandError("--timeout must be positive and --delay-seconds >= 1.")

        symbols = list(dict.fromkeys(
            symbol.strip().upper() for symbol in opts["symbols"]
            if isinstance(symbol, str) and symbol.strip()
        ))
        if not 1 <= len(symbols) <= MAX_SYMBOLS:
            raise CommandError("Supply between 1 and 10 nonempty stock symbols.")

        stocks = list(
            Stock.objects.filter(
                is_active=True, symbol__in=symbols
            ).values_list("symbol", flat=True)
        )
        missing = set(symbols) - set(stocks)
        if missing:
            raise CommandError(
                "Unknown or inactive symbols: " + ", ".join(sorted(missing))
            )

        steps = ["historical prices"]
        if opts["include_news"]:
            steps.append("news")
        if opts["include_sentiment"]:
            steps.append("sentiment")
        if opts["include_fundamentals"]:
            steps.append("fundamentals")

        self.stdout.write(
            f"Personal research sync on {REQUIRED_TEST_DB}: "
            f"{', '.join(symbols)}"
        )
        self.stdout.write(
            f"Steps: {', '.join(steps)}; history period: {opts['period']}"
        )

        if not opts["execute"]:
            self.stdout.write(
                "DRY RUN: No provider requests or database writes. "
                "Add --execute to run the selected steps."
            )
            return

        succeeded = 0
        failed = []
        rate_limited = False
        for index, symbol in enumerate(symbols):
            if index > 0:
                time.sleep(opts["delay_seconds"])

            self.stdout.write(f"Updating {symbol} ({index + 1}/{len(symbols)})")
            operations = [
                ("history", "ingest_stock_history", (symbol,), {
                    "period": opts["period"], "timeout": opts["timeout"],
                }),
            ]
            if opts["include_news"]:
                operations.append((
                    "news", "ingest_stock_news", (), {
                        "symbol": symbol, "limit": opts["news_limit"],
                    },
                ))
            if opts["include_sentiment"]:
                operations.append((
                    "sentiment", "analyze_news_sentiment", (), {
                        "symbol": symbol, "limit": opts["sentiment_limit"],
                    },
                ))
            if opts["include_fundamentals"]:
                operations.append((
                    "fundamentals", "ingest_fundamentals", (symbol,), {},
                ))

            for label, command, args, kwargs in operations:
                try:
                    call_command(
                        command, *args, **kwargs,
                        stdout=self.stdout, stderr=self.stderr,
                    )
                    succeeded += 1
                    self.stdout.write(f"  {symbol}: {label} step completed")
                except Exception as exc:
                    failed.append(f"{symbol} {label}: {type(exc).__name__}")
                    if is_provider_rate_limit(exc):
                        rate_limited = True
                        self.stderr.write(
                            f"  {symbol}: provider HTTP 429/rate limit. "
                            "Stopping remaining research refresh steps; "
                            "cached records retained."
                        )
                        break
                    self.stderr.write(
                        f"  {symbol}: {label} step FAILED "
                        f"({type(exc).__name__}: {exc})"
                    )
            if rate_limited:
                break

        self.stdout.write(
            f"Research sync summary: {succeeded} successful steps, "
            f"{len(failed)} failed steps."
        )
        if failed:
            raise CommandError(
                "Research refresh completed with errors: " + "; ".join(failed)
            )
