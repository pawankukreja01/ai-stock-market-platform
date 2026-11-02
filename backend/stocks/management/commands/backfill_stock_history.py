import time

from django.core.management import call_command, CommandError
from django.core.management.base import BaseCommand

from market_data.models import HistoricalPrice
from stocks.models import Stock


class Command(BaseCommand):
    help = (
        "Backfill missing historical prices for active stocks in small batches. "
        "Does not download fundamentals or news."
    )

    def add_arguments(self, parser):
        parser.add_argument("--period", default="5y")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument(
            "--market",
            choices=("all", "us", "uk"),
            default="all",
            help="Limit the batch to all markets, US (NASDAQ/NYSE), or UK (LSE).",
        )
        parser.add_argument(
            "--after-symbol",
            default="",
            help="Resume after this ticker in alphabetical order.",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=2,
            help="Number of retries after the initial attempt.",
        )
        parser.add_argument("--pause", type=float, default=3.0)
        parser.add_argument("--retry-delay", type=float, default=10.0)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        retries = options["retries"]
        pause = options["pause"]
        retry_delay = options["retry_delay"]

        if not 1 <= limit <= 50:
            raise CommandError("--limit must be between 1 and 50.")
        if not 0 <= retries <= 5:
            raise CommandError("--retries must be between 0 and 5.")
        if pause < 0 or retry_delay < 0:
            raise CommandError("--pause and --retry-delay cannot be negative.")

        existing_history = HistoricalPrice.objects.values_list(
            "stock_id", flat=True
        ).distinct()

        queryset = Stock.objects.filter(
            is_active=True
        ).exclude(
            pk__in=existing_history
        )

        if options["market"] == "us":
            queryset = queryset.filter(exchange__in=("NASDAQ", "NYSE"))
        elif options["market"] == "uk":
            queryset = queryset.filter(exchange="LSE")

        after_symbol = options["after_symbol"].strip().upper()
        if after_symbol:
            queryset = queryset.filter(symbol__gt=after_symbol)

        targets = list(queryset.order_by("symbol")[:limit])

        self.stdout.write(
            self.style.NOTICE(
                "Selected {} stock(s); market={}, period={}.".format(
                    len(targets), options["market"], options["period"]
                )
            )
        )

        if not targets:
            self.stdout.write("No stocks without price history match these filters.")
            return

        for stock in targets:
            self.stdout.write(
                "{} | {} | {}".format(
                    stock.symbol, stock.exchange, stock.company_name
                )
            )

        last_symbol = targets[-1].symbol
        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Dry run only; no data was downloaded or changed."
                )
            )
            self.stdout.write(
                "Resume cursor for the next batch: --after-symbol {}".format(
                    last_symbol
                )
            )
            return

        successes = []
        failures = []

        for index, stock in enumerate(targets, start=1):
            self.stdout.write(
                "\n[{}/{}] Processing {}".format(
                    index, len(targets), stock.symbol
                )
            )

            for attempt in range(retries + 1):
                try:
                    call_command(
                        "ingest_stock_history",
                        stock.symbol,
                        period=options["period"],
                        verbosity=0,
                    )

                    count = HistoricalPrice.objects.filter(
                        stock=stock
                    ).count()

                    if count == 0:
                        raise CommandError(
                            "No historical-price records found after ingestion."
                        )

                    successes.append((stock.symbol, count))
                    self.stdout.write(
                        self.style.SUCCESS(
                            "OK: {} historical records".format(count)
                        )
                    )
                    break

                except Exception as exc:
                    if attempt < retries:
                        delay = retry_delay * (attempt + 1)
                        self.stderr.write(
                            self.style.WARNING(
                                "Attempt {}/{} failed for {}: {}. "
                                "Retrying in {} second(s).".format(
                                    attempt + 1,
                                    retries + 1,
                                    stock.symbol,
                                    str(exc)[:180],
                                    delay,
                                )
                            )
                        )
                        if delay:
                            time.sleep(delay)
                    else:
                        failures.append((stock.symbol, str(exc)[:250]))
                        self.stderr.write(
                            self.style.ERROR(
                                "FAILED: {} — {}".format(
                                    stock.symbol, str(exc)[:250]
                                )
                            )
                        )

            if index < len(targets) and pause:
                time.sleep(pause)

        self.stdout.write("\n========== BACKFILL SUMMARY ==========")
        self.stdout.write("Successful: {}".format(len(successes)))
        self.stdout.write("Failed: {}".format(len(failures)))

        for symbol, count in successes:
            self.stdout.write("OK  {}: {} rows".format(symbol, count))

        for symbol, reason in failures:
            self.stderr.write("FAIL {}: {}".format(symbol, reason))

        self.stdout.write(
            "Next cursor: --after-symbol {}".format(last_symbol)
        )

        if failures:
            raise CommandError(
                "Some symbols failed. Review the failures before continuing."
            )
