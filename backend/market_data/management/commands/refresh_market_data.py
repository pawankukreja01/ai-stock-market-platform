from django.core.management import call_command, CommandError
from django.core.management.base import BaseCommand

from stocks.models import Stock


class Command(BaseCommand):
    help = (
        "Refresh stored historical prices, news, sentiment, "
        "and optionally fundamentals for active stocks."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            type=str,
            help="Refresh one stock symbol instead of all active stocks.",
        )
        parser.add_argument(
            "--period",
            type=str,
            default="5y",
            help="Historical price period passed to ingestion. Default: 5y.",
        )
        parser.add_argument(
            "--include-fundamentals",
            action="store_true",
            help="Also refresh fundamentals during a normal refresh.",
        )
        parser.add_argument(
            "--only-fundamentals",
            action="store_true",
            help="Refresh fundamentals only; skip prices, news and sentiment.",
        )
        parser.add_argument(
            "--skip-history",
            action="store_true",
            help="Skip historical price ingestion.",
        )
        parser.add_argument(
            "--skip-news",
            action="store_true",
            help="Skip news ingestion.",
        )
        parser.add_argument(
            "--skip-sentiment",
            action="store_true",
            help="Skip sentiment analysis.",
        )

    def handle(self, *args, **options):
        symbol = options.get("symbol")

        stocks = Stock.objects.filter(
            is_active=True
        ).order_by("symbol")

        if symbol:
            symbol = symbol.strip().upper()
            stocks = stocks.filter(symbol=symbol)

            if not stocks.exists():
                raise CommandError(
                    f"Active stock '{symbol}' was not found."
                )

        symbols = list(stocks.values_list("symbol", flat=True))

        if not symbols:
            self.stdout.write("No active stocks to refresh.")
            return

        failures = []

        def run_step(label, callback):
            self.stdout.write(f"  {label}...")

            try:
                callback()
            except Exception as exc:
                failures.append(f"{label}: {exc}")
                self.stderr.write(
                    self.style.ERROR(
                        f"  FAILED — {label}: {exc}"
                    )
                )
                return False

            self.stdout.write(
                self.style.SUCCESS(f"  Completed — {label}")
            )
            return True

        self.stdout.write(
            self.style.NOTICE(
                f"Refreshing {len(symbols)} stock(s): "
                f"{', '.join(symbols)}"
            )
        )

        for stock_symbol in symbols:
            self.stdout.write("")
            self.stdout.write(
                self.style.HTTP_INFO(f"=== {stock_symbol} ===")
            )

            if options["only_fundamentals"]:
                run_step(
                    f"{stock_symbol} fundamentals",
                    lambda s=stock_symbol: call_command(
                        "ingest_fundamentals", s
                    ),
                )
                continue

            if not options["skip_history"]:
                run_step(
                    f"{stock_symbol} historical prices",
                    lambda s=stock_symbol: call_command(
                        "ingest_stock_history",
                        s,
                        period=options["period"],
                    ),
                )

            if options["include_fundamentals"]:
                run_step(
                    f"{stock_symbol} fundamentals",
                    lambda s=stock_symbol: call_command(
                        "ingest_fundamentals", s
                    ),
                )

            if not options["skip_news"]:
                run_step(
                    f"{stock_symbol} news",
                    lambda s=stock_symbol: call_command(
                        "ingest_stock_news",
                        symbol=s,
                        limit=50,
                    ),
                )

        # Analyse newly ingested articles after all stocks have
        # completed their news ingestion. Existing results are
        # not forced through FinBERT again.
        if not options["only_fundamentals"] and not options["skip_sentiment"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.HTTP_INFO("=== News sentiment analysis ===")
            )

            sentiment_options = {"limit": 5000}

            if symbol:
                sentiment_options["symbol"] = symbol

            run_step(
                "sentiment analysis",
                lambda: call_command(
                    "analyze_news_sentiment",
                    **sentiment_options,
                ),
            )

        self.stdout.write("")

        if failures:
            self.stderr.write(
                self.style.ERROR(
                    f"Refresh finished with {len(failures)} failure(s):"
                )
            )

            for failure in failures:
                self.stderr.write(f" - {failure}")

            raise CommandError(
                "Some refresh steps failed. Review the output and logs."
            )

        self.stdout.write(
            self.style.SUCCESS("Market-data refresh completed successfully.")
        )