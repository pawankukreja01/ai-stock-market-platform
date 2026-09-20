from decimal import Decimal

import yfinance as yf
from django.core.management.base import BaseCommand, CommandError

from market_data.models import HistoricalPrice
from stocks.models import Stock


class Command(BaseCommand):
    help = "Download historical stock prices and store them in PostgreSQL."

    def add_arguments(self, parser):
        parser.add_argument(
            "symbol",
            type=str,
            help="Stock ticker symbol, e.g. AAPL",
        )

        parser.add_argument(
            "--period",
            type=str,
            default="10y",
            help="Yahoo Finance period, e.g. 1y, 5y, 10y",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"].upper()
        period = options["period"]

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise CommandError(
                f"{symbol} does not exist in the Stock table. "
                f"Add the stock first."
            )

        self.stdout.write(
            f"Downloading {period} of historical data for {symbol}..."
        )

        try:
            ticker = yf.Ticker(symbol)

            data = ticker.history(
                period=period,
                auto_adjust=False,
            )
        except Exception as exc:
            raise CommandError(
                f"Failed to download data for {symbol}: {exc}"
            )

        if data.empty:
            raise CommandError(
                f"No historical data returned for {symbol}."
            )

        records_created = 0
        records_updated = 0

        for index, row in data.iterrows():
            trading_date = index.date()

            values = {
                "open_price": Decimal(str(row["Open"])),
                "high_price": Decimal(str(row["High"])),
                "low_price": Decimal(str(row["Low"])),
                "close_price": Decimal(str(row["Close"])),
                "adjusted_close": Decimal(str(row["Adj Close"])),
                "volume": int(row["Volume"]),
            }

            _, created = HistoricalPrice.objects.update_or_create(
                stock=stock,
                date=trading_date,
                defaults=values,
            )

            if created:
                records_created += 1
            else:
                records_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed {symbol}: "
                f"{records_created} records created, "
                f"{records_updated} records updated."
            )
        )