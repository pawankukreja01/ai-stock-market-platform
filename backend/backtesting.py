import math

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


# =========================================================
# BASIC METRICS
# =========================================================


def calculate_cumulative_return(
    returns,
):
    """
    Calculate cumulative compounded return.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if returns.empty:
        return None

    return float(
        (1 + returns).prod() - 1
    )


def calculate_annualised_return(
    returns,
):
    """
    Calculate annualised return from daily strategy returns.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if returns.empty:
        return None

    cumulative_growth = (
        1 + returns
    ).prod()

    if cumulative_growth <= 0:
        return None

    years = (
        len(returns)
        / TRADING_DAYS_PER_YEAR
    )

    if years <= 0:
        return None

    return float(
        cumulative_growth
        ** (1 / years)
        - 1
    )


def calculate_annualised_volatility(
    returns,
):
    """
    Annualised volatility based on daily returns.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if len(returns) < 2:
        return None

    return float(
        returns.std(ddof=1)
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_maximum_drawdown(returns):
    """Calculate peak-to-trough drawdown including initial capital of 1.0."""
    returns = pd.to_numeric(returns, errors="coerce").dropna()
    if returns.empty:
        return None

    growth = (1 + returns).cumprod()
    equity = pd.concat(
        [pd.Series([1.0], dtype=float), growth.reset_index(drop=True)],
        ignore_index=True,
    )
    running_peak = equity.cummax()
    drawdown = equity / running_peak - 1
    return float(drawdown.min())

def calculate_sharpe_ratio(
    returns,
    risk_free_rate=0.0,
):
    """
    Annualised Sharpe ratio.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if len(returns) < 2:
        return None

    daily_rf = (
        (1 + risk_free_rate)
        ** (
            1
            / TRADING_DAYS_PER_YEAR
        )
        - 1
    )

    excess = (
        returns - daily_rf
    )

    std = excess.std(
        ddof=1
    )

    if (
        std == 0
        or pd.isna(std)
    ):
        return None

    return float(
        (
            excess.mean()
            / std
        )
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_sortino_ratio(
    returns,
    risk_free_rate=0.0,
):
    """
    Annualised Sortino ratio.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if len(returns) < 2:
        return None

    daily_rf = (
        (1 + risk_free_rate)
        ** (
            1
            / TRADING_DAYS_PER_YEAR
        )
        - 1
    )

    excess = (
        returns - daily_rf
    )

    downside = (
        excess[
            excess < 0
        ]
    )

    if downside.empty:
        return None

    downside_deviation = math.sqrt(
        (
            downside ** 2
        ).mean()
    )

    if (
        downside_deviation == 0
        or pd.isna(
            downside_deviation
        )
    ):
        return None

    return float(
        (
            excess.mean()
            / downside_deviation
        )
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


# =========================================================
# TRADE EXTRACTION
# =========================================================


def extract_trades(
    execution_position,
    net_strategy_returns,
    gross_strategy_returns=None,
    transaction_costs=None,
    slippage_costs=None,
):
    """Extract completed long trades and their gross/net cost attribution.

    Position values are measured immediately after execution at each close.
    A trade starts on the first row where exposure changes from flat to long
    and ends on the row where it changes back to flat. The entry fee, all
    close-to-close holding returns, and the exit fee are included.

    ``return`` remains an alias for ``net_return`` for compatibility with
    earlier callers. Open positions at the end of the supplied window are
    intentionally excluded from completed-trade statistics.
    """
    execution_position = pd.to_numeric(
        execution_position, errors="coerce"
    ).fillna(0.0)

    def aligned_series(values, default, name):
        if values is None:
            return pd.Series(default, index=execution_position.index, dtype=float)
        series = pd.to_numeric(values, errors="coerce")
        if not series.index.equals(execution_position.index):
            raise ValueError(
                f"{name} and execution positions must have matching indexes."
            )
        return series.fillna(default).astype(float)

    net_returns = aligned_series(
        net_strategy_returns, 0.0, "Net returns"
    )
    gross_returns = aligned_series(
        gross_strategy_returns, 0.0, "Gross returns"
    )
    transaction_costs = aligned_series(
        transaction_costs, 0.0, "Transaction costs"
    )
    slippage_costs = aligned_series(
        slippage_costs, 0.0, "Slippage costs"
    )

    positions = execution_position.to_numpy(dtype=float)
    trades = []
    in_trade = False
    entry_position = None

    for row_position, current_position in enumerate(positions):
        previous_position = positions[row_position - 1] if row_position else 0.0
        entered = previous_position <= 0 and current_position > 0
        exited = previous_position > 0 and current_position <= 0

        if entered:
            in_trade = True
            entry_position = row_position

        if in_trade and exited:
            exit_position = row_position
            trade_slice = slice(entry_position, exit_position + 1)
            net_trade_return = float(
                (1.0 + net_returns.iloc[trade_slice]).prod() - 1.0
            )
            gross_trade_return = float(
                (1.0 + gross_returns.iloc[trade_slice]).prod() - 1.0
            )
            transaction_cost = float(
                transaction_costs.iloc[trade_slice].sum()
            )
            slippage_cost = float(slippage_costs.iloc[trade_slice].sum())
            entry_date = execution_position.index[entry_position]
            exit_date = execution_position.index[exit_position]
            holding_sessions = max(0, exit_position - entry_position)

            try:
                calendar_days = int(
                    (pd.Timestamp(exit_date) - pd.Timestamp(entry_date)).days
                )
            except (TypeError, ValueError):
                calendar_days = None

            trades.append(
                {
                    "entry_date": str(entry_date),
                    "exit_date": str(exit_date),
                    "holding_sessions": holding_sessions,
                    "calendar_days": calendar_days,
                    "gross_return": gross_trade_return,
                    "net_return": net_trade_return,
                    "return": net_trade_return,
                    "transaction_cost": transaction_cost,
                    "slippage_cost": slippage_cost,
                    "total_cost": transaction_cost + slippage_cost,
                    "gross_to_net_return_drag": gross_trade_return - net_trade_return,
                }
            )
            in_trade = False
            entry_position = None

    return trades

def calculate_win_rate(
    trades,
):
    """
    Percentage of completed trades with
    a positive return.
    """
    if not trades:
        return None

    winners = sum(
        1
        for trade in trades
        if trade["return"] > 0
    )

    return float(
        winners / len(trades)
    )


def calculate_profit_factor(
    trades,
):
    """
    Gross winning return divided by absolute
    gross losing return.
    """
    if not trades:
        return None

    gross_profit = sum(
        trade["return"]
        for trade in trades
        if trade["return"] > 0
    )

    gross_loss = sum(
        abs(trade["return"])
        for trade in trades
        if trade["return"] < 0
    )

    if gross_loss == 0:
        if gross_profit > 0:
            return float("inf")

        return None

    return float(
        gross_profit
        / gross_loss
    )


# =========================================================
# STRATEGY BACKTEST
# =========================================================


def backtest_long_flat_strategy(
    prices,
    signal,
    transaction_cost_bps=5.0,
    slippage_bps=5.0,
    holding_period=1,
    non_overlapping_horizon=True,
):
    """Backtest long/flat signals with next-close execution.

    A signal calculated with data through close ``t`` is executed at close
    ``t+1``. The strategy therefore earns no return for the interval t -> t+1;
    its first possible market return is t+1 -> t+2.

    With ``non_overlapping_horizon=True``, an ML forecast at t enters at t+1,
    earns H daily close-to-close returns from t+1 through t+H+1, and exits at
    close t+H+1. Eligible forecasts must be at least H+1 observations apart.

    With ``non_overlapping_horizon=False``, signals are evaluated each day and
    executed at the next close. This mode is intended for continuous baselines
    such as Buy & Hold and SMA 200.

    Transaction costs and slippage are charged on the actual execution dates:
    entry at t+1 and exit at t+H+1 (or when a continuous position changes).
    Any continuous position is liquidated at the final available close.
    """
    prices = pd.to_numeric(prices, errors="coerce")
    if not prices.index.is_unique:
        raise ValueError("Price observations must have unique dates.")
    prices = prices.sort_index()
    price_values = prices.to_numpy(dtype=float)
    if not np.isfinite(price_values).all() or (price_values <= 0).any():
        raise ValueError(
            "Execution prices must be finite and positive. Missing or invalid "
            "price observations cannot be dropped or bridged in a backtest."
        )

    for name, value in (
        ("transaction_cost_bps", transaction_cost_bps),
        ("slippage_bps", slippage_bps),
    ):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a finite non-negative number.")
        if not math.isfinite(numeric_value) or numeric_value < 0:
            raise ValueError(f"{name} must be a finite non-negative number.")

    if (
        isinstance(holding_period, bool)
        or not isinstance(holding_period, (int, np.integer))
        or holding_period < 1
    ):
        raise ValueError("holding_period must be a positive integer.")

    signal = pd.to_numeric(signal, errors="coerce")
    if not signal.index.is_unique:
        raise ValueError("Signal observations must have unique dates.")
    signal = signal.reindex(prices.index)
    signal = signal.where(np.isfinite(signal))
    signal = signal.clip(lower=0, upper=1)

    if len(prices) < 2:
        raise ValueError("At least two aligned observations are required.")

    execution_position = pd.Series(0.0, index=prices.index, name="execution_position")

    if non_overlapping_horizon:
        # Select the next available OOS forecast after the previous holding
        # block has completed. This also handles sparse walk-forward folds.
        next_eligible_position = 0
        for decision_position in np.flatnonzero(signal.notna().to_numpy()):
            decision_position = int(decision_position)
            exit_position = decision_position + int(holding_period) + 1
            if decision_position < next_eligible_position or exit_position >= len(prices):
                continue

            target_position = float(signal.iloc[decision_position])
            entry_position = decision_position + 1
            execution_position.iloc[entry_position:exit_position] = target_position
            execution_position.iloc[exit_position] = 0.0
            next_eligible_position = exit_position
    else:
        # A signal known at close t is executed at close t+1.
        execution_position = (
            signal.fillna(0.0)
            .shift(1)
            .fillna(0.0)
            .clip(lower=0, upper=1)
            .astype(float)
        )
        # Mark the portfolio to cash at the last close. The return earned up
        # to that close is retained; the exit friction is charged there.
        execution_position.iloc[-1] = 0.0
        execution_position.name = "execution_position"

    # Exposure over (close[t-1], close[t]] reflects the position held after
    # execution at close[t-1]. This is the critical one-session execution lag.
    position = execution_position.shift(1).fillna(0.0).rename("position")
    data = pd.DataFrame(
        {
            "price": prices,
            "signal": signal,
            "execution_position": execution_position,
            "position": position,
        },
        index=prices.index,
    )
    data["daily_return"] = data["price"].pct_change(fill_method=None)
    data["gross_return"] = data["position"] * data["daily_return"]

    data["turnover"] = (
        data["execution_position"].diff().abs().fillna(
            data["execution_position"].abs()
        )
    )
    transaction_cost_rate = float(transaction_cost_bps) / 10_000.0
    slippage_cost_rate = float(slippage_bps) / 10_000.0
    data["transaction_cost"] = data["turnover"] * transaction_cost_rate
    data["slippage_cost"] = data["turnover"] * slippage_cost_rate
    data["trading_cost"] = data["transaction_cost"] + data["slippage_cost"]
    data["net_return"] = data["gross_return"] - data["trading_cost"]

    # The first price row has no close-to-close return. Keep all later dates,
    # including entry-only cash intervals on which transaction costs occur.
    data = data.dropna(subset=["net_return"]).copy()
    trades = extract_trades(
        data["execution_position"],
        data["net_return"],
        gross_strategy_returns=data["gross_return"],
        transaction_costs=data["transaction_cost"],
        slippage_costs=data["slippage_cost"],
    )

    net_returns = data["net_return"]
    gross_returns = data["gross_return"]
    net_cumulative_return = calculate_cumulative_return(net_returns)
    gross_cumulative_return = calculate_cumulative_return(gross_returns)
    trade_net_returns = [trade["net_return"] for trade in trades]
    winning_trade_returns = [value for value in trade_net_returns if value > 0]
    losing_trade_returns = [value for value in trade_net_returns if value < 0]
    holding_sessions = [trade["holding_sessions"] for trade in trades]

    def average(values):
        return float(np.mean(values)) if values else None

    metrics = {
        # Existing keys remain unchanged for current API consumers.
        "cumulative_return": net_cumulative_return,
        "annualised_return": calculate_annualised_return(net_returns),
        "annualised_volatility": calculate_annualised_volatility(net_returns),
        "maximum_drawdown": calculate_maximum_drawdown(net_returns),
        "sharpe_ratio": calculate_sharpe_ratio(net_returns),
        "sortino_ratio": calculate_sortino_ratio(net_returns),
        "win_rate": calculate_win_rate(trades),
        "profit_factor": calculate_profit_factor(trades),
        "trades": len(trades),
        "total_trading_cost": float(data["trading_cost"].sum()),
        "observations": len(data),
        # Gross/net attribution and execution-friction breakdown.
        "gross_cumulative_return": gross_cumulative_return,
        "gross_annualised_return": calculate_annualised_return(gross_returns),
        "net_cumulative_return": net_cumulative_return,
        "gross_to_net_return_drag": (
            float(gross_cumulative_return - net_cumulative_return)
            if gross_cumulative_return is not None and net_cumulative_return is not None
            else None
        ),
        "total_transaction_cost": float(data["transaction_cost"].sum()),
        "total_slippage_cost": float(data["slippage_cost"].sum()),
        # Operational diagnostics. Turnover is the sum of absolute changes
        # in portfolio weight (one long round trip contributes approximately 2x).
        "total_turnover": float(data["turnover"].sum()),
        "exposure_pct": float(data["position"].mean()) if len(data) else None,
        "completed_trades": len(trades),
        "average_holding_sessions": average(holding_sessions),
        "median_holding_sessions": (
            float(np.median(holding_sessions)) if holding_sessions else None
        ),
        "average_trade_return": average(trade_net_returns),
        "average_winning_trade_return": average(winning_trade_returns),
        "average_losing_trade_return": average(losing_trade_returns),
        "median_trade_return": (
            float(np.median(trade_net_returns)) if trade_net_returns else None
        ),
        "best_trade_return": max(trade_net_returns) if trade_net_returns else None,
        "worst_trade_return": min(trade_net_returns) if trade_net_returns else None,
        "average_gross_trade_return": average(
            [trade["gross_return"] for trade in trades]
        ),
    }

    return {"metrics": metrics, "daily": data, "trades": trades}

# =========================================================
# BUY AND HOLD
# =========================================================


def create_buy_and_hold_signal(
    prices,
):
    """
    Always-long signal.
    """
    return pd.Series(
        1.0,
        index=prices.index,
    )


# =========================================================
# SMA 200 STRATEGY
# =========================================================


def create_sma_signal(
    prices,
    period=200,
):
    """
    Long when price is above its SMA.

    Otherwise remain in cash.
    """
    prices = pd.to_numeric(
        prices,
        errors="coerce",
    )

    sma = prices.rolling(
        window=period,
        min_periods=period,
    ).mean()

    return (
        prices > sma
    ).astype(float)


# =========================================================
# ML SIGNAL
# =========================================================


def create_ml_signal(predictions, threshold=0.0):
    """Convert forecasts to long/cash signals while preserving unavailable rows."""
    predictions = pd.to_numeric(predictions, errors="coerce")
    predictions = predictions.where(np.isfinite(predictions))
    signal = (predictions > threshold).astype(float)
    return signal.where(predictions.notna())

# =========================================================
# STRATEGY COMPARISON
# =========================================================


def choose_walk_forward_test_size(available_oos_observations, horizon, default_test_size=200):
    """Choose a test fold long enough to contain two executable forecasts.

    Forecast origins for non-overlapping H-session trades must be at least
    H+1 observations apart. Two origins therefore require H+2 forecast rows.
    The target's full exit path is already represented in the retained price
    history because the supervised dataset excludes incomplete future targets.
    """
    for name, value in (
        ("available_oos_observations", available_oos_observations),
        ("horizon", horizon),
        ("default_test_size", default_test_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer.")

    if available_oos_observations <= 0 or horizon < 1 or default_test_size <= 0:
        raise ValueError("Observation counts, horizon, and test size must be positive.")

    minimum_test_size = horizon + 2
    if available_oos_observations < minimum_test_size:
        raise ValueError(
            "Not enough out-of-sample forecast rows for two non-overlapping "
            "holding-period forecasts."
        )

    preferred_size = min(
        default_test_size,
        max(50, available_oos_observations // 2),
    )
    return min(
        available_oos_observations,
        max(minimum_test_size, preferred_size),
    )


def choose_walk_forward_step_size(test_size, default_step_size=200):
    """Keep walk-forward test windows disjoint, including long horizons."""
    for name, value in (("test_size", test_size), ("default_step_size", default_step_size)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer.")
    if test_size <= 0 or default_step_size <= 0:
        raise ValueError("test_size and default_step_size must be positive.")
    return max(test_size, default_step_size)


def prepare_horizon_backtest_window(prices, predictions, holding_period=1):
    """Select executable non-overlapping OOS forecast blocks and their prices.

    For each selected forecast at t, the trade enters at t+1 close and exits at
    t+H+1 close. A later forecast is eligible at the prior block's exit date or
    later. Sparse walk-forward prediction folds are handled without assuming
    that fold starts fall on a fixed modulo boundary.
    """
    if (
        isinstance(holding_period, bool)
        or not isinstance(holding_period, (int, np.integer))
        or holding_period < 1
    ):
        raise ValueError("holding_period must be a positive integer.")

    prices = pd.to_numeric(prices, errors="coerce").sort_index()
    if not prices.index.is_unique:
        raise ValueError("Backtest price observations must have unique dates.")
    predictions = pd.to_numeric(predictions, errors="coerce")
    if not predictions.index.is_unique:
        raise ValueError("Forecast observations must have unique dates.")
    predictions = predictions.where(np.isfinite(predictions))

    forecast_dates = predictions.index[predictions.notna()]
    forecast_positions = prices.index.get_indexer(forecast_dates)
    forecast_positions = sorted(int(pos) for pos in forecast_positions if pos >= 0)

    selected_positions = []
    next_eligible_position = 0
    for position in forecast_positions:
        exit_position = position + int(holding_period) + 1
        if position < next_eligible_position or exit_position >= len(prices):
            continue
        selected_positions.append(position)
        next_eligible_position = exit_position

    if len(selected_positions) < 2:
        raise ValueError(
            "At least two executable out-of-sample forecasts with complete "
            "next-close entry and horizon exit prices are required."
        )

    first_decision_position = selected_positions[0]
    last_exit_position = selected_positions[-1] + int(holding_period) + 1
    window_prices = prices.iloc[first_decision_position:last_exit_position + 1]

    price_values = window_prices.to_numpy(dtype=float)
    valid_prices = np.isfinite(price_values) & (price_values > 0)
    if not valid_prices.all():
        invalid_offset = int(np.flatnonzero(~valid_prices)[0])
        invalid_date = window_prices.index[invalid_offset]
        raise ValueError(
            "Backtest window contains a missing, non-finite, or non-positive "
            f"closing price at {invalid_date}; refusing to bridge the observation."
        )

    window_predictions = predictions.reindex(window_prices.index)
    return window_prices, window_predictions

def compare_strategies(
    prices,
    ml_predictions,
    transaction_cost_bps=5.0,
    slippage_bps=5.0,
    sma_period=200,
    prediction_threshold=0.0,
    holding_period=1,
):
    """
    Compare:

        ML strategy
        Buy and Hold
        SMA strategy

    All strategies use the same price period.
    """

    # Keep the full historical price series available for indicators that need
    # a pre-test warm-up window (notably SMA 200). The execution window itself
    # remains restricted to the out-of-sample forecast period below.
    full_prices = pd.to_numeric(prices, errors="coerce").sort_index()

    aligned_prices, aligned_predictions = prepare_horizon_backtest_window(
        full_prices,
        ml_predictions,
        holding_period=holding_period,
    )

    ml_signal = create_ml_signal(
        aligned_predictions,
        threshold=prediction_threshold,
    )

    buy_hold_signal = (
        create_buy_and_hold_signal(
            aligned_prices
        )
    )

    # Calculate the SMA from all available pre-test history, then align it
    # to the OOS execution dates. Computing SMA 200 on the truncated OOS
    # window incorrectly leaves its first 199 observations in cash.
    sma_signal = create_sma_signal(
        full_prices,
        period=sma_period,
    ).reindex(aligned_prices.index)

    ml_result = (
        backtest_long_flat_strategy(
            aligned_prices,
            ml_signal,
            transaction_cost_bps=(
                transaction_cost_bps
            ),
            slippage_bps=(
                slippage_bps
            ),
            holding_period=holding_period,
            non_overlapping_horizon=True,
        )
    )

    buy_hold_result = (
        backtest_long_flat_strategy(
            aligned_prices,
            buy_hold_signal,
            transaction_cost_bps=(
                transaction_cost_bps
            ),
            slippage_bps=(
                slippage_bps
            ),
            non_overlapping_horizon=False,
        )
    )

    sma_result = (
        backtest_long_flat_strategy(
            aligned_prices,
            sma_signal,
            transaction_cost_bps=(
                transaction_cost_bps
            ),
            slippage_bps=(
                slippage_bps
            ),
            non_overlapping_horizon=False,
        )
    )

    return {
        "ml": ml_result,
        "buy_and_hold": (
            buy_hold_result
        ),
        "sma": sma_result,
    }

# =========================================================
# WALK-FORWARD PREDICTIONS
# =========================================================


def generate_walk_forward_predictions(
    X,
    y,
    folds,
    model_factory,
):
    """
    Generate genuinely out-of-sample predictions
    using the walk-forward fold definitions.

    A new model is trained for every fold.
    """

    prediction_parts = []

    for fold in folds:
        train_start = fold[
            "train_start"
        ]

        train_end = fold[
            "train_end"
        ]

        test_start = fold[
            "test_start"
        ]

        test_end = fold[
            "test_end"
        ]

        X_train = X.iloc[
            train_start:train_end
        ]

        y_train = y.iloc[
            train_start:train_end
        ]

        X_test = X.iloc[
            test_start:test_end
        ]

        if X_train.empty or X_test.empty:
            continue

        model = model_factory()

        model.fit(
            X_train,
            y_train,
        )

        predictions = model.predict(
            X_test
        )

        prediction_series = pd.Series(
            predictions,
            index=X_test.index,
            name="prediction",
        )

        prediction_parts.append(
            prediction_series
        )

    if not prediction_parts:
        return pd.Series(
            dtype=float,
            name="prediction",
        )

    result = pd.concat(
        prediction_parts
    )

    result = result[
        ~result.index.duplicated(
            keep="last"
        )
    ].sort_index()

    return result


# =========================================================
# BACKTEST REPORT
# =========================================================


def build_backtest_summary(
    strategy_results,
):
    """
    Return a compact DataFrame suitable for
    displaying strategy comparisons.
    """
    rows = []

    labels = {
        "ml": "ML Strategy",
        "buy_and_hold": "Buy & Hold",
        "sma": "SMA Strategy",
    }

    for key, label in labels.items():
        result = strategy_results[
            key
        ]

        metrics = result[
            "metrics"
        ]

        rows.append(
            {
                "strategy": label,
                "cumulative_return": (
                    metrics[
                        "cumulative_return"
                    ]
                ),
                "annualised_return": (
                    metrics[
                        "annualised_return"
                    ]
                ),
                "annualised_volatility": (
                    metrics[
                        "annualised_volatility"
                    ]
                ),
                "maximum_drawdown": (
                    metrics[
                        "maximum_drawdown"
                    ]
                ),
                "sharpe_ratio": (
                    metrics[
                        "sharpe_ratio"
                    ]
                ),
                "sortino_ratio": (
                    metrics[
                        "sortino_ratio"
                    ]
                ),
                "win_rate": (
                    metrics[
                        "win_rate"
                    ]
                ),
                "profit_factor": (
                    metrics[
                        "profit_factor"
                    ]
                ),
                "trades": (
                    metrics[
                        "trades"
                    ]
                ),
                "total_trading_cost": (
                    metrics[
                        "total_trading_cost"
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows
    )