from datetime import date
from decimal import Decimal, InvalidOperation

import math

from rest_framework.response import Response
from rest_framework.views import APIView

from stocks.models import Stock
from .models import HistoricalPrice


def parse_date(value, parameter_name):
    """Parse a required ISO-format date."""
    if not value:
        raise ValueError(
            f"{parameter_name} is required in YYYY-MM-DD format."
        )

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{parameter_name} must use YYYY-MM-DD format."
        )


def parse_decimal(value, parameter_name, default=None):
    """Parse a finite decimal number."""
    if value is None or str(value).strip() == "":
        if default is not None:
            return Decimal(str(default))

        raise ValueError(f"{parameter_name} is required.")

    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(
            f"{parameter_name} must be a valid number."
        )

    if not result.is_finite():
        raise ValueError(
            f"{parameter_name} must be a finite number."
        )

    return result


def calculate_xirr(cash_flows):
    """
    Estimate annualised money-weighted return from dated cash flows.

    Contributions are negative cash flows; the final investment
    value is a positive cash flow. Returns None if no valid root
    can be found.
    """
    if len(cash_flows) < 2:
        return None

    base_date = cash_flows[0][0]

    if cash_flows[-1][0] <= base_date:
        return None

    dated_flows = [
        (
            (flow_date - base_date).days / 365.25,
            amount,
        )
        for flow_date, amount in cash_flows
    ]

    def npv(rate):
        try:
            total = 0.0

            for years, amount in dated_flows:
                total += amount / ((1.0 + rate) ** years)

            return total

        except (OverflowError, ZeroDivisionError):
            return float("inf")

    low = -0.9999
    high = 1.0

    low_value = npv(low)
    high_value = npv(high)

    # Expand the upper bound to accommodate large annual returns.
    for _ in range(30):
        if (
            math.isfinite(low_value)
            and math.isfinite(high_value)
            and low_value * high_value <= 0
        ):
            break

        high = high * 2.0 + 1.0
        high_value = npv(high)
    else:
        return None

    if low_value == 0:
        return low * 100.0

    if high_value == 0:
        return high * 100.0

    # Bisection provides a stable root estimate.
    for _ in range(120):
        middle = (low + high) / 2.0
        middle_value = npv(middle)

        if not math.isfinite(middle_value):
            return None

        if abs(middle_value) < 1e-8:
            return middle * 100.0

        if low_value * middle_value <= 0:
            high = middle
            high_value = middle_value
        else:
            low = middle
            low_value = middle_value

    answer = (low + high) / 2.0

    if not math.isfinite(answer):
        return None

    return answer * 100.0


class InvestmentSimulatorView(APIView):
    """
    Simulate a hypothetical investment in one stock.

    Required query parameters:
        symbol
        start_date
        end_date
        initial_investment

    Optional query parameter:
        monthly_contribution (defaults to 0)

    Recurring contributions are invested on the first available
    trading date of each calendar month after the initial purchase
    month. Fractional shares are allowed.
    """

    def get(self, request):
        params = request.query_params

        symbol = params.get("symbol", "").strip().upper()

        if not symbol:
            return Response(
                {"error": "symbol is required."},
                status=400,
            )

        try:
            start_date = parse_date(
                params.get("start_date"),
                "start_date",
            )
            end_date = parse_date(
                params.get("end_date"),
                "end_date",
            )

            initial_investment = parse_decimal(
                params.get("initial_investment"),
                "initial_investment",
            )

            monthly_contribution = parse_decimal(
                params.get("monthly_contribution", "0"),
                "monthly_contribution",
                default="0",
            )

        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=400,
            )

        if end_date <= start_date:
            return Response(
                {"error": "end_date must be after start_date."},
                status=400,
            )

        if initial_investment <= 0:
            return Response(
                {"error": "initial_investment must be greater than zero."},
                status=400,
            )

        if monthly_contribution < 0:
            return Response(
                {"error": "monthly_contribution cannot be negative."},
                status=400,
            )

        try:
            stock = Stock.objects.get(
                symbol=symbol,
                is_active=True,
            )
        except Stock.DoesNotExist:
            return Response(
                {"error": f"Active stock '{symbol}' was not found."},
                status=404,
            )

        # Use adjusted closing prices for a historical,
        # dividend/split-adjusted performance approximation.
        stored_prices = list(
            HistoricalPrice.objects.filter(
                stock=stock,
                date__gte=start_date,
                date__lte=end_date,
            )
            .order_by("date")
            .values_list("date", "adjusted_close")
        )

        prices = [
            (trading_date, Decimal(str(price)))
            for trading_date, price in stored_prices
            if price is not None and Decimal(str(price)) > 0
        ]

        if len(prices) < 2:
            return Response(
                {
                    "error": (
                        "At least two valid historical prices are "
                        "required in the selected date range. "
                        "Choose a wider period or another stock."
                    ),
                    "symbol": symbol,
                    "available_observations": len(prices),
                },
                status=400,
            )

        actual_start_date, first_price = prices[0]
        actual_end_date, final_price = prices[-1]

        # Initial investment buys fractional shares on the first
        # available trading day on or after the requested start date.
        shares = initial_investment / first_price
        total_invested = initial_investment

        initial_month = (
            actual_start_date.year,
            actual_start_date.month,
        )

        last_seen_month = initial_month

        contribution_count = 0
        contribution_dates = []

        cash_flows = [
            (actual_start_date, -float(initial_investment))
        ]

        curve = []

        for index, (trading_date, adjusted_close) in enumerate(prices):
            current_month = (
                trading_date.year,
                trading_date.month,
            )

            # Invest the recurring contribution at the first
            # available trading price in each subsequent month.
            if (
                index > 0
                and current_month != last_seen_month
                and current_month != initial_month
                and monthly_contribution > 0
            ):
                shares += monthly_contribution / adjusted_close
                total_invested += monthly_contribution

                contribution_count += 1
                contribution_dates.append(
                    trading_date.isoformat()
                )

                cash_flows.append(
                    (
                        trading_date,
                        -float(monthly_contribution),
                    )
                )

            last_seen_month = current_month

            market_value = shares * adjusted_close
            profit_loss = market_value - total_invested

            return_pct = (
                profit_loss / total_invested * Decimal("100")
                if total_invested > 0
                else Decimal("0")
            )

            curve.append({
                "date": trading_date.isoformat(),
                "adjusted_close": float(adjusted_close),
                "portfolio_value": round(float(market_value), 4),
                "invested_capital": round(float(total_invested), 4),
                "profit_loss": round(float(profit_loss), 4),
                "return_pct": round(float(return_pct), 4),
            })

        final_market_value = shares * final_price
        final_profit_loss = final_market_value - total_invested

        total_return_pct = (
            final_profit_loss / total_invested * Decimal("100")
            if total_invested > 0
            else Decimal("0")
        )

        # The terminal portfolio value is treated as a positive
        # cash flow for the money-weighted return calculation.
        cash_flows.append((
            actual_end_date,
            float(final_market_value),
        ))

        annualized_return_pct = calculate_xirr(cash_flows)

        elapsed_days = (
            actual_end_date - actual_start_date
        ).days

        return Response({
            "symbol": stock.symbol,
            "company_name": stock.company_name,

            "requested_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },

            "actual_period": {
                "start_date": actual_start_date.isoformat(),
                "end_date": actual_end_date.isoformat(),
                "calendar_days": elapsed_days,
                "price_observations": len(prices),
            },

            "assumptions": {
                "price_basis": (
                    "Adjusted closing prices. Results are a "
                    "historical performance approximation, not "
                    "a record of executable trades."
                ),
                "fractional_shares": True,
                "contribution_schedule": (
                    "Initial investment on the first available "
                    "trading day in the selected range. Monthly "
                    "contributions are invested on the first "
                    "available trading day of each subsequent "
                    "calendar month."
                ),
                "dividends": (
                    "Adjusted prices provide a dividend/split-adjusted "
                    "performance approximation; this is not a brokerage "
                    "account ledger."
                ),
                "fees_and_taxes_included": False,
            },

            "summary": {
                "initial_investment": float(initial_investment),
                "monthly_contribution": float(monthly_contribution),
                "contribution_count": contribution_count,
                "additional_contributions": float(
                    monthly_contribution
                    * contribution_count
                ),
                "total_invested": float(total_invested),
                "ending_value": round(float(final_market_value), 4),
                "profit_loss": round(float(final_profit_loss), 4),
                "total_return_pct": round(
                    float(total_return_pct), 4
                ),
                "annualized_money_weighted_return_pct": (
                    round(annualized_return_pct, 4)
                    if annualized_return_pct is not None
                    else None
                ),
                "ending_adjusted_price": float(final_price),
                "initial_adjusted_price": float(first_price),
                "final_date": actual_end_date.isoformat(),
                "contribution_dates": contribution_dates,
            },

            "curve": curve,
        })