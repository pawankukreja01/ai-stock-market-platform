import math

import pandas as pd
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from market_data.models import HistoricalPrice
from .models import Portfolio, PortfolioHolding
from .serializers import PortfolioSerializer, PortfolioHoldingSerializer, normalize_currency


def holding_currency(holding):
    """Resolve the most recent stored price currency, then stock metadata."""
    price_currency = (
        HistoricalPrice.objects
        .filter(stock_id=holding.stock_id)
        .order_by("-date")
        .values_list("storage_currency", flat=True)
        .first()
    )
    normalized_price_currency = normalize_currency(price_currency)
    if normalized_price_currency != "UNKNOWN":
        return normalized_price_currency
    return normalize_currency(getattr(holding.stock, "currency", ""))


def calculate_currency_risk(holdings, currency):
    """Calculate historical risk for one currency group only."""
    series_by_symbol = {}
    excluded_symbols = []
    quantities = {}

    for holding in holdings:
        symbol = holding.stock.symbol
        rows = list(
            HistoricalPrice.objects
            .filter(stock_id=holding.stock_id)
            .order_by("-date")
            .values_list("date", "adjusted_close")[:253]
        )
        rows.reverse()

        if len(rows) < 21:
            excluded_symbols.append(symbol)
            continue

        dates = []
        values = []
        for price_date, raw_value in rows:
            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError, OverflowError):
                numeric_value = float("nan")
            if not math.isfinite(numeric_value) or numeric_value <= 0:
                numeric_value = float("nan")
            dates.append(price_date)
            values.append(numeric_value)

        series_by_symbol[symbol] = pd.Series(
            values, index=dates, name=symbol, dtype="float64"
        )
        quantities[symbol] = float(holding.quantity)

    if not series_by_symbol:
        return {
            "available": False,
            "currency": currency,
            "reason": "Insufficient stored price history. At least 21 observations per stock are required.",
            "observations": 0,
            "included_symbols": [],
            "excluded_symbols": excluded_symbols,
        }

    prices = pd.concat(list(series_by_symbol.values()), axis=1, join="outer").sort_index()
    quantity_series = pd.Series(quantities)
    portfolio_values = prices.mul(quantity_series, axis="columns").sum(
        axis=1, min_count=len(series_by_symbol)
    )
    valid_portfolio_values = portfolio_values.dropna()

    if len(valid_portfolio_values) < 21:
        return {
            "available": False,
            "currency": currency,
            "reason": "There are not enough complete portfolio valuations across the selected holdings.",
            "observations": max(len(valid_portfolio_values) - 1, 0),
            "included_symbols": list(series_by_symbol),
            "excluded_symbols": excluded_symbols,
        }

    # Calculate returns on the original date index, not on the series with
    # missing valuations removed. Dropping a missing price first would bridge
    # across the gap and fabricate a multi-session return. Keeping the NaN in
    # place invalidates both the missing session and the following return.
    daily_returns = portfolio_values.pct_change(fill_method=None).dropna()
    if len(daily_returns) < 20:
        return {
            "available": False,
            "currency": currency,
            "reason": "At least 20 daily portfolio returns are required for a risk estimate.",
            "observations": len(daily_returns),
            "included_symbols": list(series_by_symbol),
            "excluded_symbols": excluded_symbols,
        }

    annualized_volatility = float(daily_returns.std(ddof=1)) * math.sqrt(252) * 100
    running_peak = valid_portfolio_values.cummax()
    drawdowns = valid_portfolio_values / running_peak - 1
    max_drawdown_pct = float(drawdowns.min()) * 100
    start_value = float(valid_portfolio_values.iloc[0])
    end_value = float(valid_portfolio_values.iloc[-1])
    period_return_pct = (end_value / start_value - 1) * 100 if start_value > 0 else None

    elapsed_days = (valid_portfolio_values.index[-1] - valid_portfolio_values.index[0]).days
    if elapsed_days > 0 and start_value > 0 and end_value > 0:
        annualized_return_pct = ((end_value / start_value) ** (365.25 / elapsed_days) - 1) * 100
    else:
        annualized_return_pct = None

    return {
        "available": True,
        "currency": currency,
        "annualized_volatility_pct": round(annualized_volatility, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "period_return_pct": round(period_return_pct, 4) if period_return_pct is not None else None,
        "annualized_return_pct": round(annualized_return_pct, 4) if annualized_return_pct is not None else None,
        "observations": len(daily_returns),
        "start_date": valid_portfolio_values.index[0].isoformat(),
        "end_date": valid_portfolio_values.index[-1].isoformat(),
        "included_symbols": list(series_by_symbol),
        "excluded_symbols": excluded_symbols,
        "method": (
            "Historical estimate using adjusted closing prices and current share quantities. "
            "Assumes quantities remained constant throughout the period. No FX conversion is applied."
        ),
    }


class PortfolioListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(owner=self.request.user).prefetch_related("holdings__stock")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(owner=self.request.user).prefetch_related("holdings__stock")


class PortfolioHoldingListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PortfolioHoldingSerializer

    def get_portfolio(self):
        if not hasattr(self, "_portfolio_instance"):
            self._portfolio_instance = get_object_or_404(Portfolio, pk=self.kwargs["portfolio_id"], owner=self.request.user)
        return self._portfolio_instance

    def get_queryset(self):
        return (
            PortfolioHolding.objects
            .filter(portfolio=self.get_portfolio())
            .select_related("stock", "portfolio")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["portfolio"] = self.get_portfolio()
        return context

    def perform_create(self, serializer):
        serializer.save(portfolio=self.get_portfolio())


class PortfolioHoldingDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PortfolioHoldingSerializer

    def get_portfolio(self):
        if not hasattr(self, "_portfolio_instance"):
            self._portfolio_instance = get_object_or_404(Portfolio, pk=self.kwargs["portfolio_id"], owner=self.request.user)
        return self._portfolio_instance

    def get_queryset(self):
        return (
            PortfolioHolding.objects
            .filter(portfolio=self.get_portfolio())
            .select_related("stock", "portfolio")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["portfolio"] = self.get_portfolio()
        return context


class PortfolioAnalysisView(APIView):
    """Estimate portfolio risk separately for each stored currency."""
    permission_classes = [IsAuthenticated]

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(
            Portfolio.objects.prefetch_related("holdings__stock"),
            pk=portfolio_id,
            owner=request.user,
        )
        holdings = list(portfolio.holdings.select_related("stock"))
        portfolio_data = PortfolioSerializer(portfolio, context={}).data

        if not holdings:
            return Response({
                "portfolio": portfolio_data,
                "risk": {
                    "available": False,
                    "reason": "Add holdings to calculate portfolio risk.",
                    "observations": 0,
                    "included_symbols": [],
                    "excluded_symbols": [],
                    "by_currency": [],
                },
            })

        grouped = {}
        for holding in holdings:
            currency = holding_currency(holding)
            grouped.setdefault(currency, []).append(holding)

        risk_by_currency = [
            calculate_currency_risk(group, currency)
            for currency, group in sorted(grouped.items())
        ]

        if len(risk_by_currency) == 1:
            risk = risk_by_currency[0]
        else:
            risk = {
                "available": False,
                "reason": (
                    "This portfolio contains multiple currencies. Risk is calculated separately "
                    "for each currency group because no portfolio base currency or FX conversion "
                    "has been configured."
                ),
                "observations": 0,
                "included_symbols": [],
                "excluded_symbols": [],
                "currencies": [item["currency"] for item in risk_by_currency],
                "by_currency": risk_by_currency,
            }

        return Response({"portfolio": portfolio_data, "risk": risk})
