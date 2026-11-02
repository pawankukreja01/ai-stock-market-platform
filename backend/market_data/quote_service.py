from datetime import timezone as datetime_timezone
from decimal import Decimal, InvalidOperation

import yfinance as yf

from django.utils import timezone

from .models import LatestQuote
from .currency_utils import (
    CurrencyMetadataUnavailable,
    get_provider_currency_details,
    normalize_provider_price,
)


class QuoteDataUnavailable(Exception):
    """Raised when a usable quote cannot be obtained."""


def _valid_history(data):
    if data is None or data.empty:
        return None

    if "Close" not in data.columns:
        return None

    try:
        result = data.dropna(subset=["Close"]).sort_index()
    except Exception:
        return None

    return result if not result.empty else None


def _to_decimal(value, currency=None):
    try:
        if currency is not None:
            result = normalize_provider_price(value, currency)
        else:
            result = Decimal(str(value))

        if not result.is_finite():
            return None

        return result.quantize(Decimal("0.000001"))

    except (
        InvalidOperation,
        TypeError,
        ValueError,
        OverflowError,
    ):
        return None


def _to_volume(value):
    try:
        result = Decimal(str(value))

        if (
            not result.is_finite()
            or result < 0
            or result != result.to_integral_value()
            or result > 9_223_372_036_854_775_807
        ):
            return None

        return int(result)

    except (InvalidOperation, TypeError, ValueError):
        return None


def _to_aware_datetime(value):
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if timezone.is_naive(value):
        value = timezone.make_aware(
            value,
            datetime_timezone.utc,
        )

    return value


def _previous_close(daily_data, quote_date, quote_type, currency):
    if daily_data is None:
        return None

    if quote_type == "intraday_1m":
        previous_rows = daily_data[
            [index.date() < quote_date for index in daily_data.index]
        ]
    else:
        previous_rows = daily_data.iloc[:-1]

    if previous_rows.empty:
        return None

    return _to_decimal(
        previous_rows.iloc[-1]["Close"],
        currency,
    )


def _intraday_volume(intraday_data, quote_date, latest_row):
    """
    Return aggregate session volume.

    Volume is not a monetary amount and must never be currency-converted.
    """
    if "Volume" not in intraday_data.columns:
        return _to_volume(latest_row.get("Volume"))

    try:
        session_rows = intraday_data[
            [index.date() == quote_date for index in intraday_data.index]
        ]

        values = session_rows["Volume"].dropna()

        if values.empty:
            return None

        total = sum(
            _to_volume(value) or 0
            for value in values
        )

        return _to_volume(total)

    except Exception:
        return _to_volume(latest_row.get("Volume"))


def fetch_latest_quote(stock, timeout=15):
    """
    Retrieve and store the latest available Yahoo Finance quote.

    Monetary prices are normalized into the stock's major currency:
      GBp / GBX -> GBP, divided by 100.
      GBP       -> GBP, unchanged.
      USD       -> USD, unchanged.

    Volume is never converted.

    This service does not guarantee exchange-real-time data.
    """
    ticker = yf.Ticker(stock.symbol)

    try:
        currency = get_provider_currency_details(ticker)
    except CurrencyMetadataUnavailable as exc:
        raise QuoteDataUnavailable(
            f"Cannot verify currency for {stock.symbol}: {exc}"
        ) from exc

    intraday_data = None
    daily_data = None

    intraday_error = None
    daily_error = None

    try:
        intraday_data = _valid_history(
            ticker.history(
                period="5d",
                interval="1m",
                auto_adjust=False,
                prepost=False,
                timeout=timeout,
            )
        )
    except Exception as exc:
        intraday_error = str(exc)

    try:
        daily_data = _valid_history(
            ticker.history(
                period="5d",
                interval="1d",
                auto_adjust=False,
                prepost=False,
                timeout=timeout,
            )
        )
    except Exception as exc:
        daily_error = str(exc)

    if intraday_data is not None:
        quote_type = "intraday_1m"
        selected_data = intraday_data

    elif daily_data is not None:
        quote_type = "daily_close"
        selected_data = daily_data

    else:
        details = "; ".join(
            message
            for message in (intraday_error, daily_error)
            if message
        )

        raise QuoteDataUnavailable(
            f"No usable price data returned for {stock.symbol}."
            + (f" Provider details: {details}" if details else "")
        )

    latest_row = selected_data.iloc[-1]
    latest_index = selected_data.index[-1]

    # Normalize the provider's price into its major currency unit.
    price = _to_decimal(
        latest_row["Close"],
        currency,
    )

    if price is None or price <= 0:
        raise QuoteDataUnavailable(
            f"Invalid latest price returned for {stock.symbol}."
        )

    source_timestamp = _to_aware_datetime(latest_index)
    quote_date = latest_index.date()

    previous_close = _previous_close(
        daily_data,
        quote_date,
        quote_type,
        currency,
    )

    if quote_type == "intraday_1m":
        volume = _intraday_volume(
            intraday_data,
            quote_date,
            latest_row,
        )
    else:
        volume = _to_volume(latest_row.get("Volume"))

    # Keep Stock.currency in the normalized major currency.
    if stock.currency != currency.storage_code:
        stock.__class__.objects.filter(pk=stock.pk).update(
            currency=currency.storage_code
        )
        stock.currency = currency.storage_code

    # Never replace a newer stored quote with an older provider record.
    existing = LatestQuote.objects.filter(stock=stock).first()

    if (
        existing is not None
        and source_timestamp < existing.source_timestamp
    ):
        return existing

    quote, _ = LatestQuote.objects.update_or_create(
        stock=stock,
        defaults={
            "price": price,
            "previous_close": previous_close,
            "volume": volume,
            "currency": currency.storage_code,
            "provider_currency": currency.raw_code,
            "provider": "yfinance",
            "quote_type": quote_type,
            "source_timestamp": source_timestamp,
        },
    )

    return quote