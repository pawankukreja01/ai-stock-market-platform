from decimal import Decimal, InvalidOperation

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

        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            help="Yahoo Finance request timeout in seconds. Default: 30.",
        )

    def handle(self, *args, **options):
        symbol = options["symbol"].upper().strip()
        period = options["period"]
        timeout = options["timeout"]

        if timeout <= 0:
            raise CommandError("--timeout must be greater than zero.")

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
                repair=True,
                timeout=timeout,
            )
        except Exception as exc:
            raise CommandError(
                f"Failed to download data for {symbol}: {exc}"
            )

        if data.empty:
            raise CommandError(
                f"No historical data returned for {symbol}."
            )

        
        # Currency is optional metadata. Never infer it from the exchange.
        try:
            ticker_info = ticker.info
            raw_currency = (
                ticker_info.get("currency")
                if isinstance(ticker_info, dict)
                else None
            )
        except Exception:
            raw_currency = None

        if (
            isinstance(raw_currency, str)
            and len(raw_currency.strip()) == 3
            and raw_currency.strip().isalpha()
        ):
            verified_currency = raw_currency.strip().upper()
            Stock.objects.filter(pk=stock.pk).update(
                currency=verified_currency
            )
            stock.currency = verified_currency


        records_created = 0
        records_updated = 0
        records_skipped_invalid = 0

        required_columns = {
            "Open", "High", "Low", "Close", "Adj Close", "Volume"
        }
        if not required_columns.issubset(data.columns):
            missing = sorted(required_columns - set(data.columns))
            raise CommandError(
                "Historical data is missing required columns: "
                + ", ".join(missing)
            )

        for index, row in data.iterrows():
            try:
                raw_prices = {
                    "open_price": Decimal(str(row["Open"])),
                    "high_price": Decimal(str(row["High"])),
                    "low_price": Decimal(str(row["Low"])),
                    "close_price": Decimal(str(row["Close"])),
                    "adjusted_close": Decimal(str(row["Adj Close"])),
                }
                raw_volume = Decimal(str(row["Volume"]))

                if not all(value.is_finite() and value > 0
                           for value in raw_prices.values()):
                    records_skipped_invalid += 1
                    continue

                open_price = raw_prices["open_price"]
                high_price = raw_prices["high_price"]
                low_price = raw_prices["low_price"]
                close_price = raw_prices["close_price"]

                if (
                    high_price < max(open_price, close_price, low_price)
                    or low_price > min(open_price, close_price, high_price)
                    or not raw_volume.is_finite()
                    or raw_volume < 0
                    or raw_volume != raw_volume.to_integral_value()
                ):
                    records_skipped_invalid += 1
                    continue

                # Match the database DecimalField precision before saving.
                if any(
                    value.adjusted() > 10
                    for value in raw_prices.values()
                ):
                    records_skipped_invalid += 1
                    continue

                values = {
                    **raw_prices,
                    "volume": int(raw_volume),
                }
                trading_date = index.date()

            except (KeyError, TypeError, ValueError, InvalidOperation, OverflowError):
                records_skipped_invalid += 1
                continue

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
                f"{records_updated} records updated, "
                f"{records_skipped_invalid} invalid records skipped."
            )
        )