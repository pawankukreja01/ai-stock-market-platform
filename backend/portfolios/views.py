import math

import pandas as pd

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from market_data.models import HistoricalPrice

from .models import Portfolio, PortfolioHolding
from .serializers import (
    PortfolioSerializer,
    PortfolioHoldingSerializer,
)


class PortfolioListCreateView(generics.ListCreateAPIView):
    """List existing portfolios or create a new portfolio."""

    queryset = Portfolio.objects.prefetch_related(
        "holdings__stock"
    )
    serializer_class = PortfolioSerializer


class PortfolioDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, rename, or delete a portfolio."""

    queryset = Portfolio.objects.prefetch_related(
        "holdings__stock"
    )
    serializer_class = PortfolioSerializer


class PortfolioHoldingListCreateView(
    generics.ListCreateAPIView
):
    """List holdings in a portfolio or add a new holding."""

    serializer_class = PortfolioHoldingSerializer

    def get_portfolio(self):
        if not hasattr(self, "_portfolio_instance"):
            self._portfolio_instance = get_object_or_404(
                Portfolio,
                pk=self.kwargs["portfolio_id"],
            )
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


class PortfolioHoldingDetailView(
    generics.RetrieveUpdateDestroyAPIView
):
    """Retrieve, edit, or remove one holding in a portfolio."""

    serializer_class = PortfolioHoldingSerializer

    def get_portfolio(self):
        if not hasattr(self, "_portfolio_instance"):
            self._portfolio_instance = get_object_or_404(
                Portfolio,
                pk=self.kwargs["portfolio_id"],
            )
        return self._portfolio_instance

    def get_queryset(self):
        return (
            PortfolioHolding.objects
            .filter(portfolio_id=self.kwargs["portfolio_id"])
            .select_related("stock", "portfolio")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["portfolio"] = self.get_portfolio()
        return context


class PortfolioAnalysisView(APIView):
    """
    Estimate historical portfolio return, volatility and drawdown.

    Uses adjusted closing prices stored in HistoricalPrice.
    The risk calculation assumes the current share quantities
    were held throughout the historical observation period.
    It does not model deposits, withdrawals, or rebalancing.
    """

    def get(self, request, portfolio_id):
        portfolio = get_object_or_404(
            Portfolio.objects.prefetch_related(
                "holdings__stock"
            ),
            pk=portfolio_id,
        )

        holdings = list(
            portfolio.holdings.select_related("stock")
        )

        serializer_context = {}
        portfolio_data = PortfolioSerializer(
            portfolio,
            context=serializer_context,
        ).data

        if not holdings:
            return Response({
                "portfolio": portfolio_data,
                "risk": {
                    "available": False,
                    "reason": "Add holdings to calculate portfolio risk.",
                    "observations": 0,
                    "included_symbols": [],
                    "excluded_symbols": [],
                },
            })

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

            dates = [row[0] for row in rows]
            values = [float(row[1]) for row in rows]

            series_by_symbol[symbol] = pd.Series(
                values,
                index=dates,
                name=symbol,
                dtype="float64",
            )
            quantities[symbol] = float(holding.quantity)

        if not series_by_symbol:
            return Response({
                "portfolio": portfolio_data,
                "risk": {
                    "available": False,
                    "reason": (
                        "Insufficient stored price history. "
                        "At least 21 observations per stock are required."
                    ),
                    "observations": 0,
                    "included_symbols": [],
                    "excluded_symbols": excluded_symbols,
                },
            })

        # Align all holdings to shared trading dates.
        prices = pd.concat(
            list(series_by_symbol.values()),
            axis=1,
            join="inner",
        ).sort_index().dropna()

        if len(prices) < 21:
            return Response({
                "portfolio": portfolio_data,
                "risk": {
                    "available": False,
                    "reason": (
                        "There are not enough common trading dates "
                        "across the portfolio holdings."
                    ),
                    "observations": max(len(prices) - 1, 0),
                    "included_symbols": list(series_by_symbol),
                    "excluded_symbols": excluded_symbols,
                },
            })

        quantity_series = pd.Series(quantities)

        # Approximate historical portfolio values using current
        # share quantities multiplied by adjusted closing prices.
        portfolio_values = prices.mul(
            quantity_series,
            axis="columns",
        ).sum(axis=1)

        daily_returns = portfolio_values.pct_change().dropna()

        if len(daily_returns) < 20:
            return Response({
                "portfolio": portfolio_data,
                "risk": {
                    "available": False,
                    "reason": (
                        "At least 20 daily portfolio returns are "
                        "required for a risk estimate."
                    ),
                    "observations": len(daily_returns),
                    "included_symbols": list(series_by_symbol),
                    "excluded_symbols": excluded_symbols,
                },
            })

        annualized_volatility = (
            float(daily_returns.std(ddof=1))
            * math.sqrt(252)
            * 100
        )

        running_peak = portfolio_values.cummax()
        drawdowns = portfolio_values / running_peak - 1
        max_drawdown_pct = float(drawdowns.min()) * 100

        start_value = float(portfolio_values.iloc[0])
        end_value = float(portfolio_values.iloc[-1])

        period_return_pct = (
            (end_value / start_value - 1) * 100
            if start_value > 0
            else None
        )

        elapsed_days = (
            prices.index[-1] - prices.index[0]
        ).days

        if (
            elapsed_days > 0
            and start_value > 0
            and end_value > 0
        ):
            annualized_return_pct = (
                (end_value / start_value)
                ** (365.25 / elapsed_days)
                - 1
            ) * 100
        else:
            annualized_return_pct = None

        risk = {
            "available": True,
            "annualized_volatility_pct": round(
                annualized_volatility, 4
            ),
            "max_drawdown_pct": round(
                max_drawdown_pct, 4
            ),
            "period_return_pct": (
                round(period_return_pct, 4)
                if period_return_pct is not None
                else None
            ),
            "annualized_return_pct": (
                round(annualized_return_pct, 4)
                if annualized_return_pct is not None
                else None
            ),
            "observations": len(daily_returns),
            "start_date": prices.index[0].isoformat(),
            "end_date": prices.index[-1].isoformat(),
            "included_symbols": list(series_by_symbol),
            "excluded_symbols": excluded_symbols,
            "method": (
                "Historical estimate using adjusted closing prices "
                "and current share quantities. Assumes quantities "
                "remained constant throughout the period."
            ),
        }

        return Response({
            "portfolio": portfolio_data,
            "risk": risk,
        })