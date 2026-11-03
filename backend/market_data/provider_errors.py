"""Shared, non-network provider error classification for research fetches.

Never interpret empty yfinance history as evidence of a delisted stock.
A confirmed rate limit is a provider-access failure; retain stored data.
"""

import re


class ProviderRateLimited(Exception):
    """Yahoo rejected a request due to rate limiting (typically HTTP 429)."""


def is_provider_rate_limit(exc):
    """Classify yfinance's explicit rate-limit responses safely.

    Accept typed YFRateLimitError when available and explicit 429 / too-many-
    requests messages. Avoid treating generic connectivity failures as 429.
    """
    if exc is None:
        return False
    name = type(exc).__name__
    if name in {"YFRateLimitError", "ProviderRateLimited"}:
        return True
    message = str(exc)
    return bool(
        re.search(r"\bHTTP\s*429\b|\bstatus(?:\s+code)?\s*[:=]?\s*429\b|\b429\s+Too Many Requests\b|\brate.?limit(?:ed|ing)?\b", message, re.I)
    )


def safe_provider_error(exc):
    """Return bounded, non-sensitive diagnostic instead of dumping cookies."""
    if is_provider_rate_limit(exc):
        return "Yahoo Finance rate limit (HTTP 429); existing cached data retained."
    return f"{type(exc).__name__}: provider data unavailable"
