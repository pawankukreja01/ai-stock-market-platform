from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from market_data.provider_errors import is_provider_rate_limit


class CurrencyMetadataUnavailable(Exception):
    """Raised when the provider's trading currency cannot be verified."""


@dataclass(frozen=True)
class ProviderCurrency:
    raw_code: str
    storage_code: str
    price_multiplier: Decimal


def normalize_provider_currency(raw_currency):
    """
    Convert provider currency metadata into a standard storage currency.

    Yahoo Finance:
      GBp / GBX = pence sterling -> GBP, divide prices by 100.
      GBP       = pounds sterling -> GBP, no conversion.
      USD       = US dollars -> USD, no conversion.

    Other valid three-letter currency codes are retained unchanged.
    """
    if not isinstance(raw_currency, str):
        raise ValueError("Provider currency must be a string.")

    raw_code = raw_currency.strip()

    if not raw_code:
        raise ValueError("Provider currency is empty.")

    if raw_code == "GBp" or raw_code.upper() == "GBX":
        return ProviderCurrency(
            raw_code=raw_code,
            storage_code="GBP",
            price_multiplier=Decimal("0.01"),
        )

    storage_code = raw_code.upper()

    if (
        len(storage_code) != 3
        or not storage_code.isalpha()
    ):
        raise ValueError(
            f"Unsupported provider currency: {raw_code!r}"
        )

    return ProviderCurrency(
        raw_code=raw_code,
        storage_code=storage_code,
        price_multiplier=Decimal("1"),
    )


def get_provider_currency_details(ticker, *, required=True):
    """
    Retrieve provider currency metadata.

    When required=True, missing or invalid currency raises an exception.

    When required=False, return None if metadata is unavailable.
    This supports historical ingestion for non-London stocks while
    preserving their existing currency metadata.

    London-listed stocks must still have verified currency metadata
    before their prices can be normalized safely.
    """
    errors = []

    for attribute in ("fast_info", "info"):
        try:
            provider_info = getattr(ticker, attribute)
            raw_currency = provider_info.get("currency")
        except Exception as exc:
            if is_provider_rate_limit(exc):
                # Do not fetch another metadata endpoint after an explicit
                # provider rejection; avoid repeated 429 requests.
                raise CurrencyMetadataUnavailable(
                    "Yahoo Finance rate limited (HTTP 429); "
                    "currency metadata was not retrieved."
                ) from exc
            errors.append(f"{attribute}: {exc}")
            continue

        if not isinstance(raw_currency, str) or not raw_currency.strip():
            errors.append(f"{attribute}: currency unavailable")
            continue

        try:
            return normalize_provider_currency(raw_currency)
        except ValueError as exc:
            errors.append(f"{attribute}: {exc}")

    if not required:
        return None

    details = "; ".join(errors)

    raise CurrencyMetadataUnavailable(
        "Unable to verify provider trading currency."
        + (f" Details: {details}" if details else "")
    )


def normalize_provider_price(value, currency):
    """
    Convert one provider-denominated price into the storage currency.

    This function is only for monetary price values.
    Do not use it for volume, share counts or percentages.
    """
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid provider price: {value!r}")

    if not amount.is_finite():
        raise ValueError(f"Non-finite provider price: {value!r}")

    return amount * currency.price_multiplier