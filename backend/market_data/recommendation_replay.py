"""Research-only historical ranking replay; never an independent prediction claim.

Prices, signals and outcomes are evaluated in distinct time windows. Any
missing future observation excludes the *entire* comparison period, not just
underperformers; all results retain survivor/cohort provenance caveats.
"""
from datetime import timedelta
from statistics import mean, median
from decimal import Decimal
import re

from market_data.models import HistoricalPrice
from market_data.recommendation_engine import recommend_stocks

SYMBOL = re.compile(r"^[A-Z0-9.^=-]{1,20}$")


def validate_replay_symbols(values):
    if (
        not isinstance(values, list) or not 2 <= len(values) <= 100
        or any(not isinstance(s, str) or not SYMBOL.fullmatch(s) for s in values)
        or len(values) != len(set(values))
    ):
        raise ValueError("Require 2–100 unique, normalized, explicit research symbols.")
    return values


def close_return_from_future_rows(rows, *, horizon):
    """Enter at the first subsequent stored close; exit H sessions later.

    'rows' must consist solely of sessions AFTER the signal session.
    Missing or invalid OHLC closes invalidate the return; never forward-fill.
    """
    if type(horizon) is not int or not 1 <= horizon <= 60:
        raise ValueError("Horizon must be one of 1–60 trading sessions.")
    if len(rows) < horizon + 1:
        return None
    selected = rows[:horizon + 1]
    if any(
        row.get("is_ohlc_valid") is not True
        or row.get("close_price") is None
        or Decimal(str(row["close_price"])) <= 0
        for row in selected
    ):
        return None
    origin = Decimal(str(selected[0]["close_price"]))
    last = Decimal(str(selected[-1]["close_price"]))
    return float(last / origin - Decimal("1"))


def evaluate_replay_period(*, signal_date, symbols, risk_tolerance,
                           horizon_months, horizon, top_k, round_trip_bps):
    result = recommend_stocks(
        as_of=signal_date,
        symbols=symbols,
        risk_tolerance=risk_tolerance,
        horizon_months=horizon_months,
        max_candidates=100,
    )
    rank = result["results"]
    outcome = {
        "signal_date": signal_date.isoformat(),
        "status": "excluded",
        "eligible_ranked_stocks": len(rank),
        "reason": None,
        "research_only": True,
    }
    if len(rank) < max(2, top_k):
        outcome["reason"] = "Fewer than the requested number of eligible, scored stocks."
        return outcome
    symbols_scored = [item["symbol"] for item in rank]
    future_returns = {}
    for symbol in symbols_scored:
        rows = list(
            HistoricalPrice.objects.filter(
                stock__symbol=symbol, date__gt=signal_date,
            )
            .order_by("date")
            .values("date", "close_price", "is_ohlc_valid")[:horizon + 1]
        )
        value = close_return_from_future_rows(rows, horizon=horizon)
        if value is None:
            outcome["reason"] = (
                "At least one eligible stock lacks H+1 complete future closes; "
                "this whole period is excluded to prevent outcome selection bias."
            )
            return outcome
        future_returns[symbol] = value

    selected = symbols_scored[:top_k]
    # Illustrative all-in stock exposure to evaluate rankings, NOT an
    # executable recommendation or the diversified paper allocator.
    # Both arms pay an identical assumed round-trip cost.
    cost = 2.0 * round_trip_bps / 10000.0
    selected_return = mean(future_returns[s] for s in selected) - cost
    baseline_return = mean(future_returns[s] for s in symbols_scored) - cost
    outcome.update({
        "status": "evaluated",
        "reason": None,
        "selected_symbols": selected,
        "ranked_universe_count": len(symbols_scored),
        "top_k_net_return": round(selected_return, 9),
        "equal_weight_eligible_net_return": round(baseline_return, 9),
        "relative_return": round(selected_return - baseline_return, 9),
        "top_k_beat_baseline": selected_return > baseline_return,
        "cost_assumption_round_trip_bps_per_side": round_trip_bps,
    })
    return outcome


def summarize_periods(periods):
    valid = [p for p in periods if p["status"] == "evaluated"]
    delta = [p["relative_return"] for p in valid]
    if not valid:
        return {
            "eligible_periods": 0,
            "excluded_periods": len(periods),
            "win_rate_against_equal_weight": None,
            "median_excess_return": None,
            "mean_excess_return": None,
            "status": "insufficient_evidence",
        }
    return {
        "eligible_periods": len(valid),
        "excluded_periods": len(periods) - len(valid),
        "win_rate_against_equal_weight": round(
            sum(x > 0 for x in delta) / len(delta), 4
        ),
        "median_excess_return": round(median(delta), 9),
        "mean_excess_return": round(mean(delta), 9),
        "status": (
            "development_diagnostic_only"
            if len(valid) >= 3 else "insufficient_evidence"
        ),
    }
