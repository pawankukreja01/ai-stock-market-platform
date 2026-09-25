from datetime import timedelta

import yfinance as yf
import pandas as pd

from django.utils.dateparse import parse_date

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import HistoricalPrice, Fundamental
from .serializers import (
    HistoricalPriceSerializer,
    FundamentalSerializer,
)

from .risk_engine import calculate_risk_metrics, fetch_benchmark_prices


class HistoricalPriceListView(generics.ListAPIView):
    serializer_class = HistoricalPriceSerializer

    def get_queryset(self):
        stock_id = self.request.query_params.get("stock")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        queryset = HistoricalPrice.objects.select_related(
            "stock"
        )

        if stock_id:
            queryset = queryset.filter(
                stock_id=stock_id
            )

        parsed_start_date = (
            parse_date(start_date)
            if start_date
            else None
        )

        parsed_end_date = (
            parse_date(end_date)
            if end_date
            else None
        )

        if parsed_start_date:
            queryset = queryset.filter(
                date__gte=parsed_start_date
            )

        if parsed_end_date:
            queryset = queryset.filter(
                date__lte=parsed_end_date
            )

        return queryset.order_by("date")


class BenchmarkComparisonView(APIView):
    """
    Returns historical benchmark prices for comparison
    with the selected stock.
    """

    SECTOR_ETFS = {
        "Technology": "XLK",
        "Financial Services": "XLF",
        "Healthcare": "XLV",
        "Health Care": "XLV",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Industrials": "XLI",
        "Energy": "XLE",
        "Basic Materials": "XLB",
        "Communication Services": "XLC",
        "Real Estate": "XLRE",
        "Utilities": "XLU",
    }

    def get(self, request):
        start_date = request.query_params.get(
            "start_date"
        )

        end_date = request.query_params.get(
            "end_date"
        )

        sector = request.query_params.get(
            "sector",
            "",
        )

        if not start_date or not end_date:
            return Response(
                {
                    "error": (
                        "start_date and end_date "
                        "are required."
                    )
                },
                status=400,
            )

        parsed_start_date = parse_date(start_date)
        parsed_end_date = parse_date(end_date)

        if (
            not parsed_start_date
            or not parsed_end_date
        ):
            return Response(
                {
                    "error": (
                        "Dates must use YYYY-MM-DD "
                        "format."
                    )
                },
                status=400,
            )

        if parsed_start_date >= parsed_end_date:
            return Response(
                {
                    "error": (
                        "start_date must be before "
                        "end_date."
                    )
                },
                status=400,
            )

        sector_etf = self.SECTOR_ETFS.get(
            sector,
            "SPY",
        )

        benchmarks = {
            "sp500": {
                "symbol": "^GSPC",
                "name": "S&P 500",
            },
            "nasdaq100": {
                "symbol": "^NDX",
                "name": "NASDAQ-100",
            },
            "sector": {
                "symbol": sector_etf,
                "name": (
                    f"{sector_etf} Sector ETF"
                    if sector_etf != "SPY"
                    else "S&P 500 ETF"
                ),
            },
        }

        result = {}

        try:
            for key, benchmark in benchmarks.items():
                ticker = yf.Ticker(
                    benchmark["symbol"]
                )

                history = ticker.history(
                    start=parsed_start_date.isoformat(),
                    end=(
                        parsed_end_date
                        + timedelta(days=1)
                    ).isoformat(),
                    auto_adjust=False,
                    actions=False,
                )

                if history.empty:
                    result[key] = {
                        "symbol": benchmark["symbol"],
                        "name": benchmark["name"],
                        "dates": [],
                        "close": [],
                    }

                    continue

                dates = [
                    index.strftime("%Y-%m-%d")
                    for index in history.index
                ]

                closes = [
                    float(value)
                    for value in history["Close"]
                ]

                result[key] = {
                    "symbol": benchmark["symbol"],
                    "name": benchmark["name"],
                    "dates": dates,
                    "close": closes,
                }

            return Response(
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "sector": sector,
                    "benchmarks": result,
                }
            )

        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to retrieve "
                        "benchmark market data."
                    ),
                    "details": str(exc),
                },
                status=500,
            )


class FundamentalListView(generics.ListAPIView):
    """
    Returns stored fundamental data for a stock.
    """

    serializer_class = FundamentalSerializer

    def get_queryset(self):
        symbol = self.request.query_params.get(
            "symbol"
        )

        period_type = self.request.query_params.get(
            "period_type"
        )

        queryset = Fundamental.objects.select_related(
            "stock"
        )

        if symbol:
            queryset = queryset.filter(
                stock__symbol=symbol.upper()
            )

        if period_type in [
            "annual",
            "quarterly",
        ]:
            queryset = queryset.filter(
                period_type=period_type
            )

        return queryset.order_by(
            "-period_end"
        )

class RiskMetricsView(APIView):
    """
    Calculate historical risk metrics for a stock.

    Example:

    /api/risk-metrics/?symbol=AAPL
    /api/risk-metrics/?symbol=AAPL&start_date=2021-09-25&end_date=2026-09-25
    """

    def get(self, request):
        symbol = request.query_params.get("symbol")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not symbol:
            return Response(
                {
                    "error": "symbol is required."
                },
                status=400,
            )

        symbol = symbol.upper().strip()

        stock = (
            HistoricalPrice.objects
            .filter(stock__symbol=symbol)
            .select_related("stock")
            .first()
        )

        if not stock:
            return Response(
                {
                    "error": (
                        f"No historical price data found "
                        f"for {symbol}."
                    )
                },
                status=404,
            )

        if start_date:
            parsed_start_date = parse_date(start_date)

            if not parsed_start_date:
                return Response(
                    {
                        "error": (
                            "start_date must use "
                            "YYYY-MM-DD format."
                        )
                    },
                    status=400,
                )
        else:
            parsed_start_date = None

        if end_date:
            parsed_end_date = parse_date(end_date)

            if not parsed_end_date:
                return Response(
                    {
                        "error": (
                            "end_date must use "
                            "YYYY-MM-DD format."
                        )
                    },
                    status=400,
                )
        else:
            parsed_end_date = None

        if (
            parsed_start_date
            and parsed_end_date
            and parsed_start_date >= parsed_end_date
        ):
            return Response(
                {
                    "error": (
                        "start_date must be before end_date."
                    )
                },
                status=400,
            )

        queryset = (
            HistoricalPrice.objects
            .filter(stock__symbol=symbol)
            .order_by("date")
        )

        if parsed_start_date:
            queryset = queryset.filter(
                date__gte=parsed_start_date
            )

        if parsed_end_date:
            queryset = queryset.filter(
                date__lte=parsed_end_date
            )

        price_records = list(
            queryset.values(
                "date",
                "close_price",
            )
        )

        if len(price_records) < 2:
            return Response(
                {
                    "error": (
                        "At least two historical price "
                        "observations are required."
                    )
                },
                status=400,
            )

        stock_dates = [
            record["date"]
            for record in price_records
        ]

        stock_closes = [
            float(record["close_price"])
            for record in price_records
        ]

        stock_prices = pd.Series(
            stock_closes,
            index=pd.to_datetime(stock_dates),
            dtype=float,
        )

        actual_start_date = stock_dates[0]
        actual_end_date = stock_dates[-1]

        benchmark_symbol = "^GSPC"

        try:
            benchmark_prices = fetch_benchmark_prices(
                benchmark_symbol=benchmark_symbol,
                start_date=actual_start_date.isoformat(),
                end_date=(
                    actual_end_date + timedelta(days=1)
                ).isoformat(),
            )

            if benchmark_prices.empty:
                benchmark_prices = None

        except Exception:
            benchmark_prices = None

        try:
            risk_metrics = calculate_risk_metrics(
                stock_prices=stock_prices,
                benchmark_prices=benchmark_prices,
                benchmark_symbol=benchmark_symbol,
            )

        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to calculate risk metrics."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        return Response(
            {
                "symbol": symbol,
                "company_name": stock.stock.company_name,
                "start_date": actual_start_date,
                "end_date": actual_end_date,
                "benchmark": risk_metrics.get(
                    "benchmark"
                ),
                "risk_metrics": risk_metrics,
            }
        )    