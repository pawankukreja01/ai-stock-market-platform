
import math
import logging

import pandas as pd
from django.db.models import F, Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from .models import HistoricalPrice, Fundamental, NewsArticle
from ml_engine import build_stock_features


logger = logging.getLogger(__name__)


# Query parameter -> (result field, comparison)
NUMERIC_FILTERS = {
    "min_price": ("price", "min"),
    "max_price": ("price", "max"),
    "min_pe_ratio": ("pe_ratio", "min"),
    "max_pe_ratio": ("pe_ratio", "max"),
    "min_roe": ("roe", "min"),
    "max_roe": ("roe", "max"),
    "min_profit_margin": ("profit_margin", "min"),
    "max_profit_margin": ("profit_margin", "max"),
    "max_debt_to_equity": ("debt_to_equity", "max"),
    "min_dividend_yield": ("dividend_yield", "min"),
    "max_dividend_yield": ("dividend_yield", "max"),
    "min_rsi_14": ("rsi_14", "min"),
    "max_rsi_14": ("rsi_14", "max"),
    "min_return_20d": ("return_20d", "min"),
    "max_return_20d": ("return_20d", "max"),
    "max_volatility_20d": ("volatility_20d", "max"),
    "max_volatility_60d": ("volatility_60d", "max"),
    "max_drawdown_252d": ("max_drawdown_252d", "max"),
    "min_sentiment_score": ("sentiment_score", "min"),
    "max_sentiment_score": ("sentiment_score", "max"),
}

SORTABLE_FIELDS = {
    "symbol",
    "company_name",
    "price",
    "pe_ratio",
    "roe",
    "profit_margin",
    "dividend_yield",
    "rsi_14",
    "return_20d",
    "volatility_20d",
    "volatility_60d",
    "max_drawdown_252d",
    "sentiment_score",
}

FUNDAMENTAL_FIELDS = (
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
    "dividend_per_share",
    "dividend_yield",
)


def as_float(value):
    """Convert a numeric value to a finite float, or None."""
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return result if math.isfinite(result) else None


def query_float_filters(query_params):
    """Validate and parse the numeric filter parameters."""
    parsed = {}

    for parameter in NUMERIC_FILTERS:
        raw = query_params.get(parameter)

        if raw is None or raw.strip() == "":
            continue

        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(
                f"'{parameter}' must be a valid number."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"'{parameter}' must be finite."
            )

        parsed[parameter] = value

    return parsed


def latest_fundamental(stock, period_type=None):
    """Return the most recent available fundamental record."""
    queryset = Fundamental.objects.filter(stock=stock)

    if period_type:
        queryset = queryset.filter(period_type=period_type)

    return queryset.order_by(
        F("period_end").desc(nulls_last=True),
        "-id",
    ).first()


def technical_metrics(stock):
    """
    Calculate current technical and historical risk metrics.

    This uses stored historical prices and the platform's
    existing feature-engineering functions.
    """
    rows = list(
        HistoricalPrice.objects.filter(stock=stock)
        .order_by("-date")
        .values(
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "adjusted_close",
            "volume",
        )[:300]
    )

    if not rows:
        return {
            "price": None,
            "price_date": None,
            "return_20d": None,
            "rsi_14": None,
            "volatility_20d": None,
            "volatility_60d": None,
            "max_drawdown_252d": None,
            "sma20_ratio": None,
            "sma50_ratio": None,
            "sma200_ratio": None,
            "technical_data_available": False,
        }

    # Queries return newest first; indicators need chronological data.
    rows.reverse()
    price_df = pd.DataFrame(rows)

    close_values = pd.to_numeric(
        price_df["close_price"],
        errors="coerce",
    )

    latest_close = as_float(close_values.iloc[-1])
    latest_date = price_df["date"].iloc[-1]

    result = {
        "price": latest_close,
        "price_date": str(latest_date),
        "return_20d": None,
        "rsi_14": None,
        "volatility_20d": None,
        "volatility_60d": None,
        "max_drawdown_252d": None,
        "sma20_ratio": None,
        "sma50_ratio": None,
        "sma200_ratio": None,
        "technical_data_available": False,
    }

    try:
        features = build_stock_features(
            price_df,
            benchmark_prices=None,
        )

        if features.empty:
            return result

        latest = features.iloc[-1]

        for field in (
            "return_20d",
            "rsi_14",
            "volatility_20d",
            "volatility_60d",
            "sma20_ratio",
            "sma50_ratio",
            "sma200_ratio",
        ):
            if field in latest.index:
                result[field] = as_float(latest[field])

        valid_closes = close_values.dropna().tail(252)

        if not valid_closes.empty:
            running_peak = valid_closes.cummax()
            drawdowns = 1 - (valid_closes / running_peak)
            result["max_drawdown_252d"] = as_float(
                drawdowns.max()
            )

        result["technical_data_available"] = any(
            result[field] is not None
            for field in (
                "return_20d",
                "rsi_14",
                "volatility_20d",
                "volatility_60d",
            )
        )

    except Exception:
        logger.exception(
            "Could not calculate technical metrics for %s",
            stock.symbol,
        )

    return result


def sentiment_metrics(stock):
    """Average the scores of up to 50 recently published analyzed articles."""
    scores = list(
        NewsArticle.objects.filter(
            stock=stock,
            sentiment_analyzed_at__isnull=False,
            sentiment_score__isnull=False,
        )
        .order_by(
            F("published_at").desc(nulls_last=True),
            "-retrieved_at",
        )
        .values_list("sentiment_score", flat=True)[:50]
    )

    valid_scores = [
        score
        for score in (as_float(value) for value in scores)
        if score is not None
    ]

    return {
        "sentiment_score": (
            round(sum(valid_scores) / len(valid_scores), 6)
            if valid_scores
            else None
        ),
        "sentiment_articles": len(valid_scores),
    }


def apply_numeric_filters(rows, filters):
    """Return rows that satisfy all supplied numeric conditions."""
    filtered = []

    for row in rows:
        matches = True

        for parameter, threshold in filters.items():
            field, operation = NUMERIC_FILTERS[parameter]
            value = row.get(field)

            # A requested filter requires the corresponding
            # metric to be available.
            if value is None:
                matches = False
                break

            if operation == "min" and value < threshold:
                matches = False
                break

            if operation == "max" and value > threshold:
                matches = False
                break

        if matches:
            filtered.append(row)

    return filtered


class StockScreenerView(APIView):
    """
    Filter, sort and paginate active stocks.

    Example:
    /api/screener/?sector=Technology&min_price=50&page=1&page_size=20
    """

    def get(self, request):
        params = request.query_params

        # -------------------------------------------------
        # Validate fundamental period selection
        # -------------------------------------------------

        period_type = params.get("period_type", "").strip().lower()

        if period_type and period_type not in {"annual", "quarterly"}:
            return Response(
                {
                    "error": (
                        "period_type must be 'annual' or 'quarterly'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Validate filters
        # -------------------------------------------------

        try:
            numeric_filters = query_float_filters(params)
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check paired ranges.
        range_pairs = (
            ("min_price", "max_price"),
            ("min_pe_ratio", "max_pe_ratio"),
            ("min_roe", "max_roe"),
            ("min_profit_margin", "max_profit_margin"),
            ("min_dividend_yield", "max_dividend_yield"),
            ("min_rsi_14", "max_rsi_14"),
            ("min_return_20d", "max_return_20d"),
            ("min_sentiment_score", "max_sentiment_score"),
        )

        for lower_name, upper_name in range_pairs:
            if (
                lower_name in numeric_filters
                and upper_name in numeric_filters
                and numeric_filters[lower_name] > numeric_filters[upper_name]
            ):
                return Response(
                    {
                        "error": (
                            f"{lower_name} cannot be greater than "
                            f"{upper_name}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # -------------------------------------------------
        # Validate sorting and pagination
        # -------------------------------------------------

        sort_by = params.get("sort_by", "symbol").strip()

        if sort_by not in SORTABLE_FIELDS:
            return Response(
                {
                    "error": (
                        "Unsupported sort_by field. Supported fields: "
                        + ", ".join(sorted(SORTABLE_FIELDS))
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sort_order = params.get("sort_order", "asc").strip().lower()

        if sort_order not in {"asc", "desc"}:
            return Response(
                {
                    "error": "sort_order must be 'asc' or 'desc'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            page = int(params.get("page", "1"))
            page_size = int(params.get("page_size", "20"))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "page and page_size must be integers."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if page < 1 or not 1 <= page_size <= 100:
            return Response(
                {
                    "error": (
                        "page must be at least 1 and page_size "
                        "must be between 1 and 100."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -------------------------------------------------
        # Build initial stock queryset
        # -------------------------------------------------

        stocks = Stock.objects.filter(is_active=True)

        search = params.get("search", "").strip()
        sector = params.get("sector", "").strip()
        exchange = params.get("exchange", "").strip()

        if search:
            stocks = stocks.filter(
                Q(symbol__icontains=search)
                | Q(company_name__icontains=search)
                | Q(sector__icontains=search)
                | Q(industry__icontains=search)
            )

        if sector:
            stocks = stocks.filter(sector__icontains=sector)

        if exchange:
            stocks = stocks.filter(exchange__icontains=exchange)

        stock_list = list(stocks.order_by("symbol"))

        # -------------------------------------------------
        # Build screener records
        # -------------------------------------------------

        results = []

        for stock in stock_list:
            fundamental = latest_fundamental(
                stock,
                period_type=period_type or None,
            )

            fundamentals = {
                field: (
                    as_float(getattr(fundamental, field))
                    if fundamental is not None
                    else None
                )
                for field in FUNDAMENTAL_FIELDS
            }

            technical = technical_metrics(stock)
            sentiment = sentiment_metrics(stock)

            row = {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "exchange": stock.exchange,
                "sector": stock.sector,
                "industry": stock.industry,
                "fundamental_period_end": (
                    str(fundamental.period_end)
                    if fundamental and fundamental.period_end
                    else None
                ),
                "fundamental_period_type": (
                    fundamental.period_type
                    if fundamental
                    else None
                ),
                **fundamentals,
                **technical,
                **sentiment,
            }

            results.append(row)

        results = apply_numeric_filters(
            results,
            numeric_filters,
        )

        # -------------------------------------------------
        # Sort with missing values always last
        # -------------------------------------------------

        available = [
            row for row in results
            if row.get(sort_by) is not None
        ]
        missing = [
            row for row in results
            if row.get(sort_by) is None
        ]

        available.sort(
            key=lambda row: row[sort_by],
            reverse=(sort_order == "desc"),
        )

        results = available + missing

        # -------------------------------------------------
        # Paginate
        # -------------------------------------------------

        total = len(results)
        total_pages = math.ceil(total / page_size) if total else 0

        start = (page - 1) * page_size
        end = start + page_size
        page_results = results[start:end]

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "sort": {
                    "field": sort_by,
                    "order": sort_order,
                },
                "filters_applied": {
                    "search": search or None,
                    "sector": sector or None,
                    "exchange": exchange or None,
                    "period_type": period_type or None,
                    **numeric_filters,
                },
                "results": page_results,
            },
            status=status.HTTP_200_OK,
        )
