
from datetime import date, datetime
from decimal import (
    Decimal,
    InvalidOperation,
    ROUND_HALF_UP,
)

import yfinance as yf

from django.core.management.base import BaseCommand, CommandError

from market_data.models import HistoricalPrice
from market_data.currency_utils import (
    CurrencyMetadataUnavailable,
    get_provider_currency_details,
    normalize_provider_price,
)
from stocks.models import Stock


PRICE_QUANTUM = Decimal("0.0001")

# DecimalField(max_digits=15, decimal_places=4) maximum.
MAX_PRICE = Decimal("99999999999.9999")

# BigIntegerField maximum.
MAX_BIGINT = 9223372036854775807


class Command(BaseCommand):
    help = (
        "Download historical stock prices, normalize provider currencies, "
        "and store historical data-quality metadata."
    )

    PRICE_FIELDS = {
        "open_price": "Open",
        "high_price": "High",
        "low_price": "Low",
        "close_price": "Close",
        "adjusted_close": "Adj Close",
    }

    OHLC_FIELDS = {
        "open_price": "OPEN",
        "high_price": "HIGH",
        "low_price": "LOW",
        "close_price": "CLOSE",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "symbol",
            type=str,
            help="Stock ticker symbol, e.g. AAPL or ABF.L",
        )

        parser.add_argument(
            "--period",
            type=str,
            default="10y",
            help="Yahoo Finance period, e.g. 1y, 5y, 10y.",
        )

        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            help="Yahoo Finance request timeout in seconds.",
        )

    # =========================================================
    # DECIMAL AND PRICE NORMALIZATION
    # =========================================================

    @staticmethod
    def _parse_decimal(value):
        """
        Safely convert a provider value into a finite Decimal.

        Returns:
            (Decimal, None) when valid.
            (None, reason) when invalid.
        """
        if value is None:
            return None, "MISSING"

        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None, "INVALID"

        if not result.is_finite():
            return None, "NON_FINITE"

        return result, None

    @classmethod
    def _normalize_price(cls, raw_value, currency):
        """
        Normalize a provider price into the database storage currency.

        GBPp/GBX conversion is handled by currency_utils.

        Returns:
            (normalized_price, error)
        """
        raw_decimal, error = cls._parse_decimal(raw_value)

        if error:
            return None, error

        try:
            if currency is not None:
                normalized = normalize_provider_price(
                    raw_decimal,
                    currency,
                )
            else:
                # Only permitted for non-London stocks when provider
                # currency metadata is unavailable. No conversion
                # is guessed.
                normalized = raw_decimal

            if not normalized.is_finite():
                return None, "NON_FINITE"

            normalized = normalized.quantize(
                PRICE_QUANTUM,
                rounding=ROUND_HALF_UP,
            )

            # Check the value after rounding as well.
            if abs(normalized) > MAX_PRICE:
                return None, "OUT_OF_RANGE"

            return normalized, None

        except (
            InvalidOperation,
            TypeError,
            ValueError,
            OverflowError,
        ):
            return None, "NORMALIZATION_FAILED"

    # =========================================================
    # DATE HANDLING
    # =========================================================

    @staticmethod
    def _get_trading_date(index):
        """Convert a Yahoo Finance index into a Python date."""
        if isinstance(index, datetime):
            return index.date()

        if isinstance(index, date):
            return index

        to_pydatetime = getattr(index, "to_pydatetime", None)

        if callable(to_pydatetime):
            converted = to_pydatetime()

            if isinstance(converted, datetime):
                return converted.date()

            if isinstance(converted, date):
                return converted

        date_method = getattr(index, "date", None)

        if callable(date_method):
            converted = date_method()

            if isinstance(converted, date):
                return converted

        raise ValueError(
            f"Cannot determine trading date from index: {index!r}"
        )

    # =========================================================
    # QUALITY FLAG HELPERS
    # =========================================================

    @staticmethod
    def _append_flag(flags, flag):
        """Append a quality flag only once."""
        if flag not in flags:
            flags.append(flag)

    @classmethod
    def _add_price_error_flag(
        cls,
        flags,
        field_name,
        error,
    ):
        """Convert a price parsing error into a quality flag."""
        if error is None:
            return

        error_flags = {
            "MISSING": f"MISSING_{field_name}",
            "INVALID": f"INVALID_{field_name}",
            "NON_FINITE": f"NON_FINITE_{field_name}",
            "OUT_OF_RANGE": f"OUT_OF_RANGE_{field_name}",
            "NORMALIZATION_FAILED": (
                f"NORMALIZATION_FAILED_{field_name}"
            ),
        }

        flag = error_flags.get(
            error,
            f"INVALID_{field_name}",
        )

        cls._append_flag(flags, flag)

    @classmethod
    def _validate_volume(cls, raw_volume):
        """
        Validate volume independently of OHLC prices.

        Invalid volume is represented as NULL in the database.
        """
        volume, error = cls._parse_decimal(raw_volume)

        if error:
            return None, False

        if volume < 0:
            return None, False

        if volume != volume.to_integral_value():
            return None, False

        if volume > Decimal(MAX_BIGINT):
            return None, False

        return int(volume), True

    @classmethod
    def _build_quality_flags(
        cls,
        prices,
        price_errors,
        volume_valid,
    ):
        """
        Evaluate OHLC relationships and volume independently.

        A positive, usable close can still be retained even when
        the candle's OHLC relationships are inconsistent.
        """
        flags = []

        # -----------------------------------------------------
        # OHLC field validity
        # -----------------------------------------------------

        for field_name, label in cls.OHLC_FIELDS.items():
            value = prices[field_name]
            error = price_errors[field_name]

            if value is None:
                cls._add_price_error_flag(
                    flags,
                    label,
                    error or "MISSING",
                )

            elif value <= 0:
                cls._append_flag(
                    flags,
                    f"{label}_NON_POSITIVE",
                )

        open_price = prices["open_price"]
        high_price = prices["high_price"]
        low_price = prices["low_price"]
        close_price = prices["close_price"]

        # -----------------------------------------------------
        # OHLC relationship validation
        # -----------------------------------------------------

        if high_price is not None and low_price is not None:
            if high_price < low_price:
                cls._append_flag(
                    flags,
                    "HIGH_BELOW_LOW",
                )

        if high_price is not None and open_price is not None:
            if high_price < open_price:
                cls._append_flag(
                    flags,
                    "HIGH_BELOW_OPEN",
                )

        if high_price is not None and close_price is not None:
            if high_price < close_price:
                cls._append_flag(
                    flags,
                    "HIGH_BELOW_CLOSE",
                )

        if low_price is not None and open_price is not None:
            if low_price > open_price:
                cls._append_flag(
                    flags,
                    "LOW_ABOVE_OPEN",
                )

        if low_price is not None and close_price is not None:
            if low_price > close_price:
                cls._append_flag(
                    flags,
                    "LOW_ABOVE_CLOSE",
                )

        ohlc_flag_prefixes = (
            "MISSING_",
            "INVALID_",
            "NON_FINITE_",
            "OUT_OF_RANGE_",
            "NORMALIZATION_FAILED_",
        )

        ohlc_relationship_flags = {
            "HIGH_BELOW_LOW",
            "HIGH_BELOW_OPEN",
            "HIGH_BELOW_CLOSE",
            "LOW_ABOVE_OPEN",
            "LOW_ABOVE_CLOSE",
            "OPEN_NON_POSITIVE",
            "HIGH_NON_POSITIVE",
            "LOW_NON_POSITIVE",
            "CLOSE_NON_POSITIVE",
        }

        is_ohlc_valid = not any(
            flag.startswith(ohlc_flag_prefixes)
            or flag in ohlc_relationship_flags
            for flag in flags
        )

        # -----------------------------------------------------
        # Volume validity
        # -----------------------------------------------------

        is_volume_valid = bool(volume_valid)

        if not is_volume_valid:
            cls._append_flag(
                flags,
                "INVALID_VOLUME",
            )

        return is_ohlc_valid, is_volume_valid, flags

    # =========================================================
    # MAIN COMMAND
    # =========================================================

    def handle(self, *args, **options):
        symbol = options["symbol"].upper().strip()
        period = options["period"]
        timeout = options["timeout"]

        if not symbol:
            raise CommandError(
                "Stock symbol cannot be empty."
            )

        if timeout <= 0:
            raise CommandError(
                "--timeout must be greater than zero."
            )

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise CommandError(
                f"{symbol} does not exist in the Stock table. "
                "Add the stock first."
            )

        self.stdout.write(
            f"Downloading {period} of historical data for {symbol}..."
        )

        ticker = yf.Ticker(symbol)

        # -----------------------------------------------------
        # DOWNLOAD HISTORICAL DATA
        # -----------------------------------------------------

        try:
            data = ticker.history(
                period=period,
                auto_adjust=False,
                repair=True,
                timeout=timeout,
            )

        except Exception as exc:
            raise CommandError(
                f"Failed to download data for {symbol}: {exc}"
            ) from exc

        if data is None or data.empty:
            raise CommandError(
                f"No historical data returned for {symbol}. "
                "Existing records have been preserved."
            )

        required_columns = {
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume",
        }

        missing_columns = required_columns - set(data.columns)

        if missing_columns:
            raise CommandError(
                "Historical data is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        # -----------------------------------------------------
        # PROVIDER CURRENCY METADATA
        # -----------------------------------------------------

        try:
            currency = get_provider_currency_details(
                ticker,
                required=False,
            )

        except CurrencyMetadataUnavailable as exc:
            raise CommandError(
                f"Cannot verify currency for {symbol}: {exc}"
            ) from exc

        if currency is None:
            # For London listings, guessing between GBp and GBP
            # could corrupt every historical monetary value.
            if symbol.endswith(".L"):
                raise CommandError(
                    f"Cannot safely ingest {symbol}: provider currency "
                    "is unavailable. Existing records have been preserved."
                )

            provider_currency = ""
            storage_currency = (stock.currency or "").upper()

            self.stdout.write(
                self.style.WARNING(
                    f"Provider currency unavailable for {symbol}. "
                    "Raw prices will be retained without conversion, "
                    "and existing stock currency metadata will be preserved."
                )
            )

        else:
            provider_currency = currency.raw_code
            storage_currency = currency.storage_code

            self.stdout.write(
                f"Provider currency: {provider_currency}"
            )

            self.stdout.write(
                f"Storage currency: {storage_currency}"
            )

            self.stdout.write(
                f"Price multiplier: {currency.price_multiplier}"
            )

            # Stock.currency represents the major storage currency.
            if stock.currency != storage_currency:
                Stock.objects.filter(pk=stock.pk).update(
                    currency=storage_currency
                )

                stock.currency = storage_currency

        # -----------------------------------------------------
        # PROCESSING COUNTERS
        # -----------------------------------------------------

        records_created = 0
        records_updated = 0

        records_flagged = 0
        records_ohlc_invalid = 0
        records_volume_invalid = 0

        records_skipped_unusable = 0

        skipped_details = []
        flagged_details = []

        # -----------------------------------------------------
        # PROCESS EACH DAILY OBSERVATION
        # -----------------------------------------------------

        for index, row in data.iterrows():

            # Determine the trading date.
            try:
                trading_date = self._get_trading_date(index)

            except (TypeError, ValueError, AttributeError) as exc:
                records_skipped_unusable += 1

                skipped_details.append(
                    f"Unknown trading date: {exc}"
                )
                continue

            # -------------------------------------------------
            # Normalize monetary fields.
            # -------------------------------------------------

            normalized_prices = {}
            price_errors = {}

            for model_field, provider_column in self.PRICE_FIELDS.items():

                normalized, error = self._normalize_price(
                    row[provider_column],
                    currency,
                )

                normalized_prices[model_field] = normalized
                price_errors[model_field] = error

            # -------------------------------------------------
            # Validate essential closing price.
            # -------------------------------------------------

            close_price = normalized_prices["close_price"]

            if close_price is None or close_price <= 0:
                records_skipped_unusable += 1

                skipped_details.append(
                    f"{trading_date}: unusable closing price "
                    f"({price_errors['close_price'] or 'NON_POSITIVE'})"
                )
                continue

            # The current database schema requires adjusted_close.
            # Do not substitute Close for Adjusted Close.
            adjusted_close = normalized_prices["adjusted_close"]

            if adjusted_close is None or adjusted_close <= 0:
                records_skipped_unusable += 1

                skipped_details.append(
                    f"{trading_date}: unusable adjusted close "
                    f"({price_errors['adjusted_close'] or 'NON_POSITIVE'})"
                )
                continue

            # -------------------------------------------------
            # Validate volume separately.
            # -------------------------------------------------

            volume_value, volume_valid = self._validate_volume(
                row["Volume"]
            )

            # -------------------------------------------------
            # Build candle quality metadata.
            # -------------------------------------------------

            is_ohlc_valid, is_volume_valid, quality_flags = (
                self._build_quality_flags(
                    normalized_prices,
                    price_errors,
                    volume_valid,
                )
            )

            # -------------------------------------------------
            # Prepare database values.
            # -------------------------------------------------

            values = {
                **normalized_prices,
                "volume": volume_value,

                "provider_currency": provider_currency,
                "storage_currency": storage_currency,

                "is_ohlc_valid": is_ohlc_valid,
                "is_volume_valid": is_volume_valid,
                "quality_flags": quality_flags,
            }

            # -------------------------------------------------
            # Save, including OHLC-invalid candles.
            # -------------------------------------------------

            try:
                _, created = HistoricalPrice.objects.update_or_create(
                    stock=stock,
                    date=trading_date,
                    defaults=values,
                )

            except (InvalidOperation, OverflowError, ValueError) as exc:
                records_skipped_unusable += 1

                skipped_details.append(
                    f"{trading_date}: database value error: {exc}"
                )
                continue

            if created:
                records_created += 1
            else:
                records_updated += 1

            # -------------------------------------------------
            # Quality counters.
            # -------------------------------------------------

            if quality_flags:
                records_flagged += 1

                flagged_details.append(
                    f"{trading_date}: {', '.join(quality_flags)}"
                )

            if not is_ohlc_valid:
                records_ohlc_invalid += 1

            if not is_volume_valid:
                records_volume_invalid += 1

        # -----------------------------------------------------
        # FINAL SUMMARY
        # -----------------------------------------------------

        total_saved = records_created + records_updated
        records_ohlc_valid = total_saved - records_ohlc_invalid

        self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed {symbol}: "
                f"{records_created} records created, "
                f"{records_updated} records updated, "
                f"{records_skipped_unusable} invalid records skipped."
            )
        )

        self.stdout.write(
            f"Total records processed successfully: {total_saved}"
        )

        self.stdout.write(
            f"Records with quality flags: {records_flagged}"
        )

        self.stdout.write(
            f"OHLC-valid records: {records_ohlc_valid}"
        )

        self.stdout.write(
            f"OHLC-invalid records: {records_ohlc_invalid}"
        )

        self.stdout.write(
            f"Volume-invalid records: {records_volume_invalid}"
        )

        # -----------------------------------------------------
        # FLAGGED RECORD DETAILS
        # -----------------------------------------------------

        if flagged_details:
            self.stdout.write(
                self.style.WARNING(
                    "\n========== FLAGGED RECORDS =========="
                )
            )

            for detail in flagged_details:
                self.stdout.write(
                    self.style.WARNING(detail)
                )

        # -----------------------------------------------------
        # SKIPPED RECORD DETAILS
        # -----------------------------------------------------

        if skipped_details:
            self.stdout.write(
                self.style.ERROR(
                    "\n========== SKIPPED RECORDS =========="
                )
            )

            for detail in skipped_details:
                self.stdout.write(
                    self.style.ERROR(detail)
                )

        self.stdout.write(
            "\nHistorical ingestion finished."
        )
