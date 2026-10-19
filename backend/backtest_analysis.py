import math


STRATEGY_LABELS = {
    "ml": "ML Strategy",
    "buy_and_hold": "Buy & Hold",
    "sma": "SMA 200",
}


COMPARISON_METRICS = [
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
]


def _finite(value):
    if value is None:
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _get_metric(strategy_result, metric):
    if not strategy_result:
        return None

    return strategy_result.get("metrics", {}).get(metric)


def _difference(first, second):
    if not _finite(first) or not _finite(second):
        return None

    return float(first - second)


def _better_higher(first, second):
    if not _finite(first) or not _finite(second):
        return None

    return bool(first > second)


def _better_lower(first, second):
    if not _finite(first) or not _finite(second):
        return None

    return bool(first < second)


def compare_strategy_pair(
    selected_result,
    benchmark_result,
    selected_label,
    benchmark_label,
):
    """
    Compare one strategy against another using explicit
    metrics. No composite or arbitrary score is calculated.
    """
    selected_metrics = selected_result.get(
        "metrics", {}
    )
    benchmark_metrics = benchmark_result.get(
        "metrics", {}
    )

    return {
        "selected_strategy": selected_label,
        "benchmark_strategy": benchmark_label,
        "cumulative_return_difference": _difference(
            selected_metrics.get("cumulative_return"),
            benchmark_metrics.get("cumulative_return"),
        ),
        "annualised_return_difference": _difference(
            selected_metrics.get("annualised_return"),
            benchmark_metrics.get("annualised_return"),
        ),
        "volatility_difference": _difference(
            selected_metrics.get("annualised_volatility"),
            benchmark_metrics.get("annualised_volatility"),
        ),
        "drawdown_improvement": _difference(
            selected_metrics.get("maximum_drawdown"),
            benchmark_metrics.get("maximum_drawdown"),
        ),
        "sharpe_difference": _difference(
            selected_metrics.get("sharpe_ratio"),
            benchmark_metrics.get("sharpe_ratio"),
        ),
        "sortino_difference": _difference(
            selected_metrics.get("sortino_ratio"),
            benchmark_metrics.get("sortino_ratio"),
        ),
        "win_rate_difference": _difference(
            selected_metrics.get("win_rate"),
            benchmark_metrics.get("win_rate"),
        ),
        "profit_factor_difference": _difference(
            selected_metrics.get("profit_factor"),
            benchmark_metrics.get("profit_factor"),
        ),
        "trade_count_difference": _difference(
            selected_metrics.get("trades"),
            benchmark_metrics.get("trades"),
        ),
        "trading_cost_difference": _difference(
            selected_metrics.get("total_trading_cost"),
            benchmark_metrics.get("total_trading_cost"),
        ),
        "outperformed_on_cumulative_return": _better_higher(
            selected_metrics.get("cumulative_return"),
            benchmark_metrics.get("cumulative_return"),
        ),
        "outperformed_on_annualised_return": _better_higher(
            selected_metrics.get("annualised_return"),
            benchmark_metrics.get("annualised_return"),
        ),
        "lower_volatility": _better_lower(
            selected_metrics.get("annualised_volatility"),
            benchmark_metrics.get("annualised_volatility"),
        ),
        "lower_maximum_drawdown": _better_higher(
            selected_metrics.get("maximum_drawdown"),
            benchmark_metrics.get("maximum_drawdown"),
        ),
        "higher_sharpe": _better_higher(
            selected_metrics.get("sharpe_ratio"),
            benchmark_metrics.get("sharpe_ratio"),
        ),
        "higher_sortino": _better_higher(
            selected_metrics.get("sortino_ratio"),
            benchmark_metrics.get("sortino_ratio"),
        ),
    }


def _best_strategy(
    strategy_results,
    metric,
    higher_is_better=True,
):
    candidates = []

    for key, result in strategy_results.items():
        value = _get_metric(result, metric)

        if _finite(value):
            candidates.append(
                (
                    key,
                    float(value),
                )
            )

    if not candidates:
        return None

    if higher_is_better:
        selected_key, selected_value = max(
            candidates,
            key=lambda item: item[1],
        )
    else:
        selected_key, selected_value = min(
            candidates,
            key=lambda item: item[1],
        )

    return {
        "strategy": selected_key,
        "label": STRATEGY_LABELS.get(
            selected_key,
            selected_key,
        ),
        "value": selected_value,
    }


def build_metric_leaders(
    strategy_results,
):
    """
    Identify the strategy leading each individual metric.
    This deliberately avoids combining metrics into one score.
    """
    return {
        "cumulative_return": _best_strategy(
            strategy_results,
            "cumulative_return",
            higher_is_better=True,
        ),
        "annualised_return": _best_strategy(
            strategy_results,
            "annualised_return",
            higher_is_better=True,
        ),
        "annualised_volatility": _best_strategy(
            strategy_results,
            "annualised_volatility",
            higher_is_better=False,
        ),
        "maximum_drawdown": _best_strategy(
            strategy_results,
            "maximum_drawdown",
            higher_is_better=True,
        ),
        "sharpe_ratio": _best_strategy(
            strategy_results,
            "sharpe_ratio",
            higher_is_better=True,
        ),
        "sortino_ratio": _best_strategy(
            strategy_results,
            "sortino_ratio",
            higher_is_better=True,
        ),
        "win_rate": _best_strategy(
            strategy_results,
            "win_rate",
            higher_is_better=True,
        ),
        "profit_factor": _best_strategy(
            strategy_results,
            "profit_factor",
            higher_is_better=True,
        ),
        "trades": _best_strategy(
            strategy_results,
            "trades",
            higher_is_better=False,
        ),
        "total_trading_cost": _best_strategy(
            strategy_results,
            "total_trading_cost",
            higher_is_better=False,
        ),
    }


def build_ml_interpretation(
    strategy_results,
):
    """
    Build a transparent textual interpretation of ML
    performance versus the two reference strategies.
    """
    ml_result = strategy_results.get("ml")
    buy_hold_result = strategy_results.get(
        "buy_and_hold"
    )
    sma_result = strategy_results.get("sma")

    if not ml_result:
        return "ML strategy results are unavailable."

    statements = []

    for benchmark_key, benchmark_result in (
        ("buy_and_hold", buy_hold_result),
        ("sma", sma_result),
    ):
        if not benchmark_result:
            continue

        comparison = compare_strategy_pair(
            ml_result,
            benchmark_result,
            "ML Strategy",
            STRATEGY_LABELS[benchmark_key],
        )

        benchmark_label = STRATEGY_LABELS[benchmark_key]

        return_better = comparison[
            "outperformed_on_annualised_return"
        ]
        drawdown_better = comparison[
            "lower_maximum_drawdown"
        ]
        sharpe_better = comparison[
            "higher_sharpe"
        ]

        if return_better is True:
            statements.append(
                f"ML has a higher annualised return than {benchmark_label}."
            )
        elif return_better is False:
            statements.append(
                f"ML has a lower annualised return than {benchmark_label}."
            )

        if drawdown_better is True:
            statements.append(
                f"ML has a less severe maximum drawdown than {benchmark_label}."
            )
        elif drawdown_better is False:
            statements.append(
                f"ML has a more severe maximum drawdown than {benchmark_label}."
            )

        if sharpe_better is True:
            statements.append(
                f"ML has a higher Sharpe ratio than {benchmark_label}."
            )
        elif sharpe_better is False:
            statements.append(
                f"ML has a lower Sharpe ratio than {benchmark_label}."
            )

    if not statements:
        return (
            "There is not enough valid data to produce a comparative interpretation."
        )

    return " ".join(statements)


def build_backtest_analysis(
    strategy_results,
    configuration=None,
):
    """
    Build the Step 19.4 analytical layer from an existing
    strategy backtest result.
    """
    ml_result = strategy_results.get("ml")
    buy_hold_result = strategy_results.get(
        "buy_and_hold"
    )
    sma_result = strategy_results.get("sma")

    result = {
        "metric_leaders": build_metric_leaders(
            strategy_results
        ),
        "comparisons": {},
        "interpretation": build_ml_interpretation(
            strategy_results
        ),
    }

    if ml_result and buy_hold_result:
        result["comparisons"]["ml_vs_buy_and_hold"] = (
            compare_strategy_pair(
                ml_result,
                buy_hold_result,
                "ML Strategy",
                "Buy & Hold",
            )
        )

    if ml_result and sma_result:
        result["comparisons"]["ml_vs_sma"] = (
            compare_strategy_pair(
                ml_result,
                sma_result,
                "ML Strategy",
                "SMA 200",
            )
        )

    if configuration:
        result["assumptions"] = {
            "transaction_cost_bps": configuration.get(
                "transaction_cost_bps"
            ),
            "slippage_bps": configuration.get(
                "slippage_bps"
            ),
            "prediction_threshold": configuration.get(
                "prediction_threshold"
            ),
        }

    return result
