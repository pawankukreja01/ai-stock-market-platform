"""Real-data feature extraction for investment recommendations."""

from datetime import date
import logging
import math

import pandas as pd

from .models import Fundamental, HistoricalPrice, NewsArticle
from .risk_engine import calculate_risk_metrics
from django.db.models import F
from .screener_views import (
    as_float,
    technical_metrics,
)

logger = logging.getLogger(__name__)

MIN_PRICE_OBSERVATIONS = 60
MAX_PRICE_OBSERVATIONS = 300


def _safe_float(value):
    """Return a finite float, preserving missing values as None."""
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return result if math.isfinite(result) else None


def _fundamental_features(stock, *, as_of):
    """Only use records known to MarketPulse by the research cutoff.

    Period end is NOT a filing/publication timestamp. Both period end and
    actual ingestion timestamp must precede the cutoff. Imported backfilled
    records will not be incorrectly used in older historical evaluations.
    """
    fundamental = (
        Fundamental.objects.filter(
            stock=stock,
            period_end__isnull=False,
            period_end__lte=as_of,
            created_at__isnull=False,
            created_at__date__lte=as_of,
        )
        .order_by(F("period_end").desc(nulls_last=True), "-pk")
        .first()
    )

    if fundamental is None:
        return {
            "fundamental_data_available": False,
            "fundamental_period_end": None,
        }

    fields = (
        "revenue",
        "gross_profit",
        "operating_income",
        "net_income",
        "eps",
        "free_cash_flow",
        "roe",
        "roa",
        "gross_margin",
        "operating_margin",
        "profit_margin",
        "debt_to_equity",
        "current_ratio",
        "pe_ratio",
        "forward_pe",
        "peg_ratio",
        "price_to_sales",
        "price_to_book",
        "dividend_yield",
    )

    result = {
        field: _safe_float(getattr(fundamental, field))
        for field in fields
    }

    result.update({
        "fundamental_data_available": any(
            value is not None for value in result.values()
        ),
        "fundamental_period_end": (
            fundamental.period_end.isoformat()
            if fundamental.period_end else None
        ),
        "fundamental_period_type": fundamental.period_type,
    })

    return result


def _historical_risk_features(stock, as_of=None):
    """Calculate risk from positive stored closes, preserving invalid-row gaps."""
    queryset = HistoricalPrice.objects.filter(stock=stock)
    if as_of is not None:
        queryset = queryset.filter(date__lte=as_of)

    rows = list(
        queryset.order_by("-date", "-id")
        .values("date", "close_price")[:MAX_PRICE_OBSERVATIONS]
    )
    rows.reverse()

    if not rows:
        return {
            "risk_data_available": False,
            "risk_observations": 0,
            "annualised_volatility": None,
            "maximum_drawdown": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "annualised_return": None,
        }

    dates = pd.to_datetime([row["date"] for row in rows])
    close_values = []
    for row in rows:
        close = _safe_float(row["close_price"])
        close_values.append(close if close is not None and close > 0 else float("nan"))

    # Keep invalid close rows as NaN. Dropping them here would make the risk
    # engine calculate a multi-session move as though it were a daily return.
    prices = pd.Series(close_values, index=dates, dtype=float)
    prices = prices[~prices.index.duplicated(keep="last")].sort_index()
    valid_observations = int(prices.notna().sum())

    if valid_observations < MIN_PRICE_OBSERVATIONS:
        return {
            "risk_data_available": False,
            "risk_observations": valid_observations,
            "annualised_volatility": None,
            "maximum_drawdown": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "annualised_return": None,
        }

    try:
        metrics = calculate_risk_metrics(prices)
    except (ValueError, TypeError, ArithmeticError):
        logger.exception("Risk calculation failed for %s", stock.symbol)
        metrics = {}

    return {
        "risk_data_available": bool(metrics),
        "risk_observations": metrics.get("observations", valid_observations),
        "risk_return_observations": metrics.get("return_observations", 0),
        "annualised_volatility": _safe_float(metrics.get("annualised_volatility")),
        "maximum_drawdown": _safe_float(metrics.get("maximum_drawdown")),
        "sharpe_ratio": _safe_float(metrics.get("sharpe_ratio")),
        "sortino_ratio": _safe_float(metrics.get("sortino_ratio")),
        "annualised_return": _safe_float(metrics.get("annualised_return")),
    }


def _sentiment_features(stock, *, as_of):
    """Only use previously published, retrieved AND analyzed sentiment.

    Archived articles retrieved or analyzed after as_of cannot count as
    point-in-time evidence, even if their publication date was earlier.
    This deliberately excludes ambiguous timestamp provenance.
    """
    scores = list(
        NewsArticle.objects.filter(
            stock=stock,
            published_at__isnull=False,
            published_at__date__lte=as_of,
            retrieved_at__date__lte=as_of,
            sentiment_analyzed_at__isnull=False,
            sentiment_analyzed_at__date__lte=as_of,
            sentiment_score__isnull=False,
        )
        .order_by(F("published_at").desc(nulls_last=True), "-pk")
        .values_list("sentiment_score", flat=True)[:50]
    )
    valid = [_safe_float(value) for value in scores]
    valid = [value for value in valid if value is not None]
    return {
        "sentiment_score": (
            round(sum(valid) / len(valid), 6) if valid else None
        ),
        "sentiment_articles": len(valid),
    }


def extract_candidate_features(stock, *, as_of=None):
    """
    Return stored technical, fundamental, sentiment and risk evidence.

    This function does not predict future returns, assign a score,
    or claim that a candidate is suitable for a particular investor.
    """
    as_of = as_of or date.today()

    technical = technical_metrics(stock, as_of=as_of)
    fundamentals = _fundamental_features(stock, as_of=as_of)
    sentiment = _sentiment_features(stock, as_of=as_of)
    risk = _historical_risk_features(stock, as_of=as_of)

    price = _safe_float(technical.get("price"))
    price_date = technical.get("price_date")

    if isinstance(price_date, date):
        price_date = price_date.isoformat()

    try:
        parsed_price_date = (
            date.fromisoformat(str(price_date)[:10])
            if price_date else None
        )
    except (TypeError, ValueError):
        parsed_price_date = None

    price_age_days = (
        (as_of - parsed_price_date).days
        if parsed_price_date else None
    )

    # This is a transparent data-quality gate, not an investment forecast.
    exclusion_reasons = []

    if price is None or price <= 0:
        exclusion_reasons.append("No valid latest closing price.")

    if price_age_days is None:
        exclusion_reasons.append("Price date is unavailable.")
    elif price_age_days < 0:
        exclusion_reasons.append("Price date is in the future.")
    elif price_age_days > 7:
        exclusion_reasons.append("Stored price is more than seven days old.")

    if not risk["risk_data_available"]:
        exclusion_reasons.append(
            f"At least {MIN_PRICE_OBSERVATIONS} valid price observations "
            "are required for risk assessment."
        )

    return {
        "symbol": stock.symbol,
        "company_name": stock.company_name,
        "exchange": stock.exchange,
        "currency": stock.currency,
        "sector": stock.sector,
        "industry": stock.industry,
        "latest_price": price,
        "latest_price_date": price_date,
        "price_age_days": price_age_days,
        "technical": technical,
        "fundamentals": fundamentals,
        "sentiment": sentiment,
        "risk": risk,
        "data_quality": {
            "evidence_cutoff_date": as_of.isoformat(),
            "source_timing_note": (
                "Archived filings/news without verifiable timestamps before "
                "the cutoff were excluded; original filing dates may be "
                "unavailable, so this is not a certified point-in-time feed."
            ),
            "price_available": price is not None and price > 0,
            "technical_data_available": bool(
                technical.get("technical_data_available")
            ),
            "fundamental_data_available": fundamentals[
                "fundamental_data_available"
            ],
            "sentiment_articles": sentiment["sentiment_articles"],
            "risk_data_available": risk["risk_data_available"],
            "eligible_for_scoring": not exclusion_reasons,
            "exclusion_reasons": exclusion_reasons,
        },
    }
