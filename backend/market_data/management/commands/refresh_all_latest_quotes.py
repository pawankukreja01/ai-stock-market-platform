
import time

from django.core.management.base import BaseCommand, CommandError

from stocks.models import Stock
from market_data.models import LatestQuote
from market_data.quote_service import (
    QuoteDataUnavailable,
    QuoteProviderRateLimited,
    fetch_latest_quote,
)


class Command(BaseCommand):
    help = (
        "Refresh the latest available quotes for multiple active stocks."
    )

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()

        group.add_argument(
            "--symbol",
            type=str,
            help="Refresh only one stock, e.g. AAPL or REL.L.",
        )

        group.add_argument(
            "--all",
            action="store_true",
            dest="all_stocks",
            help="Refresh every active stock.",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum stocks to process when --all is not supplied. Default: 10.",
        )

        parser.add_argument(
            "--timeout",
            type=float,
            default=15,
            help="Provider request timeout in seconds. Default: 15.",
        )

        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay between stocks in seconds. Default: 1.",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"]
        all_stocks = options["all_stocks"]
        limit = options["limit"]
        timeout = options["timeout"]
        delay = options["delay"]

        if limit <= 0:
            raise CommandError("--limit must be greater than zero.")

        if timeout <= 0:
            raise CommandError("--timeout must be greater than zero.")

        if delay < 0:
            raise CommandError("--delay cannot be negative.")

        # Select stocks to process.
        if symbol:
            try:
                stocks = [
                    Stock.objects.get(
                        symbol__iexact=symbol.strip(),
                        is_active=True,
                    )
                ]
            except Stock.DoesNotExist:
                raise CommandError(
                    f"Active stock '{symbol}' was not found."
                )

        elif all_stocks:
            stocks = list(
                Stock.objects.filter(
                    is_active=True
                ).order_by("symbol")
            )

        else:
            stocks = list(
                Stock.objects.filter(
                    is_active=True
                ).order_by("symbol")[:limit]
            )

        total = len(stocks)

        if total == 0:
            raise CommandError("No active stocks were found.")

        self.stdout.write(
            self.style.NOTICE(
                f"Starting quote refresh for {total} stock(s)."
            )
        )

        self.stdout.write(
            f"Provider timeout: {timeout}s | "
            f"Delay between stocks: {delay}s"
        )

        updated = 0
        unchanged = 0
        failed = 0

        for index, stock in enumerate(stocks, start=1):
            self.stdout.write(
                f"\n[{index}/{total}] Processing {stock.symbol}..."
            )

            # Capture the existing quote so we can distinguish
            # an actual change from an unchanged provider response.
            previous = (
                LatestQuote.objects
                .filter(stock=stock)
                .values(
                    "price",
                    "previous_close",
                    "volume",
                    "currency",
                    "provider",
                    "quote_type",
                    "source_timestamp",
                )
                .first()
            )

            try:
                quote = fetch_latest_quote(
                    stock,
                    timeout=timeout,
                )

                current = {
                    "price": quote.price,
                    "previous_close": quote.previous_close,
                    "volume": quote.volume,
                    "currency": quote.currency,
                    "provider": quote.provider,
                    "quote_type": quote.quote_type,
                    "source_timestamp": quote.source_timestamp,
                }

                if previous is None or previous != current:
                    updated += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated {stock.symbol}: "
                            f"{quote.price} "
                            f"{quote.currency or ''}"
                        )
                    )

                else:
                    unchanged += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"No new quote data for {stock.symbol}. "
                            f"Existing quote retained."
                        )
                    )

                self.stdout.write(
                    f"Quote type: {quote.quote_type} | "
                    f"Source: {quote.source_timestamp}"
                )

            except QuoteProviderRateLimited as exc:
                failed += 1
                remaining = total - index
                self.stderr.write(
                    self.style.ERROR(
                        f"Yahoo rate limited quote requests at {stock.symbol}: {exc}. "
                        f"Stopping this batch; {remaining} stock(s) not requested."
                    )
                )
                break

            except QuoteDataUnavailable as exc:
                failed += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"Quote unavailable for {stock.symbol}: {exc}"
                    )
                )

            except Exception as exc:
                failed += 1

                self.stderr.write(
                    self.style.ERROR(
                        f"Unexpected error for {stock.symbol}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                )

            # Avoid sending requests for every stock simultaneously.
            if index < total and delay > 0:
                time.sleep(delay)

        # Final summary.
        self.stdout.write("\n" + "=" * 55)
        self.stdout.write(self.style.NOTICE("QUOTE REFRESH SUMMARY"))
        self.stdout.write("=" * 55)

        self.stdout.write(f"Total processed: {total}")
        self.stdout.write(
            self.style.SUCCESS(f"Updated: {updated}")
        )
        self.stdout.write(
            self.style.WARNING(f"Unchanged: {unchanged}")
        )
        self.stdout.write(
            self.style.ERROR(f"Failed: {failed}")
        )

        self.stdout.write("=" * 55)

        if failed:
            raise CommandError(
                f"Refresh completed with {failed} failure(s). "
                f"{updated} updated, {unchanged} unchanged."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "All selected stocks processed successfully."
            )
        )
