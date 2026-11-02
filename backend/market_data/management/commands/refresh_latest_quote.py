
from django.core.management.base import BaseCommand, CommandError

from stocks.models import Stock

from market_data.quote_service import (
    QuoteDataUnavailable,
    fetch_latest_quote,
)


class Command(BaseCommand):
    help = "Fetch and store the latest available quote for one stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "symbol",
            type=str,
            help="Stock ticker symbol, e.g. AAPL or REL.L.",
        )

        parser.add_argument(
            "--timeout",
            type=float,
            default=15,
            help="Provider request timeout in seconds.",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"].strip().upper()
        timeout = options["timeout"]

        if timeout <= 0:
            raise CommandError("--timeout must be greater than zero.")

        try:
            stock = Stock.objects.get(
                symbol=symbol,
                is_active=True,
            )
        except Stock.DoesNotExist:
            raise CommandError(
                f"Active stock '{symbol}' was not found in the Stock table."
            )

        self.stdout.write(
            f"Fetching latest available quote for {symbol}..."
        )

        try:
            quote = fetch_latest_quote(
                stock,
                timeout=timeout,
            )
        except QuoteDataUnavailable as exc:
            raise CommandError(str(exc))

        currency = quote.currency or "Unknown currency"

        self.stdout.write(
            self.style.SUCCESS(
                f"Quote stored for {symbol}: "
                f"{quote.price} {currency}"
            )
        )

        self.stdout.write(
            f"Quote type: {quote.quote_type}"
        )

        self.stdout.write(
            f"Source timestamp: {quote.source_timestamp}"
        )

        self.stdout.write(
            f"Retrieved at: {quote.retrieved_at}"
        )
