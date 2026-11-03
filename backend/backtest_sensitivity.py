import math

from backtesting import compare_strategies


DEFAULT_COST_LEVELS_BPS = [0.0, 2.0, 5.0, 10.0, 20.0]
DEFAULT_SLIPPAGE_LEVELS_BPS = [0.0, 2.0, 5.0, 10.0, 20.0]

# Sensitivity responses stay compact; all values are taken directly
# from the existing backtest engine rather than reimplemented here.
SENSITIVITY_METRICS = [
    "cumulative_return",
    "annualised_return",
    "annualised_volatility",
    "maximum_drawdown",
    "sharpe_ratio",
    "sortino_ratio",
    "win_rate",
    "profit_factor",
    "trades",
    "total_trading_cost",
    "gross_cumulative_return",
    "gross_to_net_return_drag",
    "total_transaction_cost",
    "total_slippage_cost",
    "total_turnover",
]


def _json_safe_number(value):
    """Return a finite float/int or None so API JSON stays standards-safe."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value if isinstance(value, (str, bool, int)) else None
    if not math.isfinite(number):
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    return number


def _selected_metrics(strategy_result):
    metrics = strategy_result.get("metrics", {})
    return {
        metric: _json_safe_number(metrics.get(metric))
        for metric in SENSITIVITY_METRICS
    }


def _scenario_id(cost_bps, slippage_bps):
    def fmt(value):
        return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")

    return f"cost_{fmt(cost_bps)}_slippage_{fmt(slippage_bps)}"


def run_cost_slippage_sensitivity(
    prices,
    predictions,
    selected_transaction_cost_bps=5.0,
    selected_slippage_bps=5.0,
    prediction_threshold=0.0,
    sma_period=200,
    holding_period=1,
    cost_levels_bps=None,
    slippage_levels_bps=None,
):
    """Re-run strategy accounting across a transaction-cost/slippage grid.

    Walk-forward predictions are supplied by the caller and are reused for
    every scenario, so this function does not retrain any ML models.

    Values are expressed in basis points (bps); 100 bps = 1 percentage point.
    """
    cost_levels = list(
        DEFAULT_COST_LEVELS_BPS if cost_levels_bps is None else cost_levels_bps
    )
    slippage_levels = list(
        DEFAULT_SLIPPAGE_LEVELS_BPS if slippage_levels_bps is None else slippage_levels_bps
    )

    for value in cost_levels + slippage_levels:
        if not math.isfinite(float(value)) or float(value) < 0:
            raise ValueError("Cost and slippage levels must be finite non-negative numbers.")

    selected_transaction_cost_bps = float(selected_transaction_cost_bps)
    selected_slippage_bps = float(selected_slippage_bps)

    scenarios_to_run = []
    seen_pairs = set()

    for cost in cost_levels:
        for slippage in slippage_levels:
            pair = (float(cost), float(slippage))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            scenarios_to_run.append(pair)

    selected_pair = (
        selected_transaction_cost_bps,
        selected_slippage_bps,
    )
    if selected_pair not in seen_pairs:
        scenarios_to_run.append(selected_pair)
        seen_pairs.add(selected_pair)

    scenarios = []
    for cost_bps, slippage_bps in scenarios_to_run:
        results = compare_strategies(
            prices,
            predictions,
            transaction_cost_bps=cost_bps,
            slippage_bps=slippage_bps,
            sma_period=sma_period,
            prediction_threshold=prediction_threshold,
            holding_period=holding_period,
        )

        strategies = {
            key: _selected_metrics(results[key])
            for key in ("ml", "buy_and_hold", "sma")
        }

        selected = (
            cost_bps == selected_transaction_cost_bps
            and slippage_bps == selected_slippage_bps
        )
        scenarios.append(
            {
                "scenario_id": _scenario_id(cost_bps, slippage_bps),
                "label": (
                    f"Cost {cost_bps:g} bps / Slippage {slippage_bps:g} bps"
                ),
                "transaction_cost_bps": cost_bps,
                "slippage_bps": slippage_bps,
                "combined_friction_bps": cost_bps + slippage_bps,
                "is_selected_configuration": selected,
                "strategies": strategies,
            }
        )

    selected_scenario = next(
        (scenario for scenario in scenarios if scenario["is_selected_configuration"]),
        None,
    )
    frictionless_scenario = next(
        (
            scenario for scenario in scenarios
            if scenario["transaction_cost_bps"] == 0
            and scenario["slippage_bps"] == 0
        ),
        None,
    )
    stress_scenario = next(
        (
            scenario for scenario in scenarios
            if scenario["transaction_cost_bps"] == max(cost_levels)
            and scenario["slippage_bps"] == max(slippage_levels)
        ),
        None,
    )

    ml_cumulative_values = [
        scenario["strategies"]["ml"].get("cumulative_return")
        for scenario in scenarios
    ]
    valid_ml_cumulative_values = [
        value for value in ml_cumulative_values if value is not None
    ]
    ml_positive_count = sum(
        value is not None and value > 0 for value in ml_cumulative_values
    )

    frictionless_ml_return = (
        frictionless_scenario["strategies"]["ml"].get("cumulative_return")
        if frictionless_scenario else None
    )
    stress_ml_return = (
        stress_scenario["strategies"]["ml"].get("cumulative_return")
        if stress_scenario else None
    )

    return {
        "method": "Fixed walk-forward predictions with non-overlapping horizon-matched holding blocks; strategy costs and slippage are varied per scenario.",
        "units": {
            "basis_points": "100 bps = 1 percentage point",
            "returns": "decimal ratios; for example, 0.05 = 5%",
        },
        "grid": {
            "transaction_cost_levels_bps": cost_levels,
            "slippage_levels_bps": slippage_levels,
            "scenario_count": len(scenarios),
        },
        "selected_configuration": {
            "transaction_cost_bps": selected_transaction_cost_bps,
            "slippage_bps": selected_slippage_bps,
            "combined_friction_bps": selected_transaction_cost_bps + selected_slippage_bps,
            "holding_period_trading_days": int(holding_period),
            "scenario_id": selected_scenario["scenario_id"] if selected_scenario else None,
        },
        "summary": {
            "ml_positive_cumulative_return_scenarios": int(ml_positive_count),
            "ml_total_scenarios_with_valid_return": len(valid_ml_cumulative_values),
            "ml_positive_under_all_valid_scenarios": (
                bool(valid_ml_cumulative_values)
                and all(value > 0 for value in valid_ml_cumulative_values)
            ),
            "frictionless_ml_cumulative_return": _json_safe_number(frictionless_ml_return),
            "stress_ml_cumulative_return": _json_safe_number(stress_ml_return),
            "stress_minus_frictionless_ml_cumulative_return": (
                _json_safe_number(stress_ml_return - frictionless_ml_return)
                if stress_ml_return is not None and frictionless_ml_return is not None
                else None
            ),
        },
        "scenarios": scenarios,
        "assumptions": [
            "The same out-of-sample walk-forward predictions are reused for each scenario; only transaction cost and slippage assumptions change.",
            "Cost and slippage are applied by the existing backtest engine on each position change.",
            "The grid is a sensitivity analysis, not a claim about actual broker execution costs.",
            "Results are historical simulations and do not guarantee future performance.",
        ],
    }