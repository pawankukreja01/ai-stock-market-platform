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


def calculate_maximum_drawdown(
    returns,
):
    """
    Calculate maximum peak-to-trough drawdown
    from strategy returns.
    """
    returns = pd.to_numeric(
        returns,
        errors="coerce",
    ).dropna()

    if returns.empty:
        return None

    equity_curve = (
        1 + returns
    ).cumprod()

    running_peak = (
        equity_curve.cummax()
    )

    drawdown = (
        equity_curve
        / running_peak
        - 1
    )

    return float(
        drawdown.min()
    )


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
    position,
    net_strategy_returns,
):
    """
    Extract individual long trades from a long/flat
    strategy.

    A trade begins when position changes from 0 -> 1
    and ends when position changes from 1 -> 0.

    The return of a trade is the compounded net strategy
    return during the active period.
    """
    position = pd.to_numeric(
        position,
        errors="coerce",
    ).fillna(0)

    returns = pd.to_numeric(
        net_strategy_returns,
        errors="coerce",
    ).fillna(0)

    trades = []

    in_trade = False
    entry_date = None
    trade_returns = []

    for i in range(
        len(position)
    ):
        current_position = (
            position.iloc[i]
        )

        current_date = (
            position.index[i]
        )

        if (
            not in_trade
            and current_position > 0
        ):
            in_trade = True
            entry_date = current_date
            trade_returns = []

        if in_trade:
            trade_returns.append(
                returns.iloc[i]
            )

        is_last = (
            i == len(position) - 1
        )

        next_position = (
            position.iloc[i + 1]
            if not is_last
            else 0
        )

        if (
            in_trade
            and (
                next_position <= 0
                or is_last
            )
        ):
            trade_return = float(
                (
                    1
                    + pd.Series(
                        trade_returns
                    )
                ).prod()
                - 1
            )

            trades.append(
                {
                    "entry_date": str(
                        entry_date
                    ),
                    "exit_date": str(
                        current_date
                    ),
                    "return": trade_return,
                }
            )

            in_trade = False
            entry_date = None
            trade_returns = []

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
):
    """
    Backtest a long/flat strategy.

    Parameters
    ----------
    prices:
        pandas Series of closing prices indexed by date.

    signal:
        pandas Series containing:
            1 = long
            0 = cash

        The signal generated at date t is shifted forward
        one trading day before being applied.

    transaction_cost_bps:
        Transaction cost per position change.

    slippage_bps:
        Slippage per position change.

    Returns
    -------
    dict
    """

    prices = pd.to_numeric(
        prices,
        errors="coerce",
    )

    signal = pd.to_numeric(
        signal,
        errors="coerce",
    )

    data = pd.concat(
        [
            prices.rename(
                "price"
            ),
            signal.rename(
                "signal"
            ),
        ],
        axis=1,
    ).dropna()

    if len(data) < 2:
        raise ValueError(
            "At least two aligned observations "
            "are required."
        )

    data["signal"] = (
        data["signal"]
        .clip(
            lower=0,
            upper=1,
        )
    )

    # -----------------------------------------------------
    # One-day-ahead execution
    #
    # Signal at t is applied at t+1.
    # -----------------------------------------------------

    data["position"] = (
        data["signal"]
        .shift(1)
        .fillna(0)
    )

    data["daily_return"] = (
        data["price"].pct_change()
    )

    # Gross strategy return.
    data["gross_return"] = (
        data["position"]
        * data["daily_return"]
    )

    # -----------------------------------------------------
    # Turnover
    # -----------------------------------------------------

    data["turnover"] = (
        data["position"]
        .diff()
        .abs()
        .fillna(
            data["position"].abs()
        )
    )

    total_cost_bps = (
        transaction_cost_bps
        + slippage_bps
    )

    cost_rate = (
        total_cost_bps
        / 10_000
    )

    data["trading_cost"] = (
        data["turnover"]
        * cost_rate
    )

    data["net_return"] = (
        data["gross_return"]
        - data["trading_cost"]
    )

    data = data.dropna(
        subset=[
            "net_return"
        ]
    )

    trades = extract_trades(
        data["position"],
        data["net_return"],
    )

    cumulative_return = (
        calculate_cumulative_return(
            data["net_return"]
        )
    )

    annualised_return = (
        calculate_annualised_return(
            data["net_return"]
        )
    )

    annualised_volatility = (
        calculate_annualised_volatility(
            data["net_return"]
        )
    )

    maximum_drawdown = (
        calculate_maximum_drawdown(
            data["net_return"]
        )
    )

    sharpe = calculate_sharpe_ratio(
        data["net_return"]
    )

    sortino = calculate_sortino_ratio(
        data["net_return"]
    )

    win_rate = calculate_win_rate(
        trades
    )

    profit_factor = (
        calculate_profit_factor(
            trades
        )
    )

    return {
        "metrics": {
            "cumulative_return": (
                cumulative_return
            ),
            "annualised_return": (
                annualised_return
            ),
            "annualised_volatility": (
                annualised_volatility
            ),
            "maximum_drawdown": (
                maximum_drawdown
            ),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "win_rate": win_rate,
            "profit_factor": (
                profit_factor
            ),
            "trades": len(
                trades
            ),
            "total_trading_cost": float(
                data[
                    "trading_cost"
                ].sum()
            ),
            "observations": len(
                data
            ),
        },

        "daily": data,

        "trades": trades,
    }


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


def create_ml_signal(
    predictions,
    threshold=0.0,
):
    """
    Convert predicted returns into a long/flat signal.

    Positive predicted return above threshold -> long.
    Otherwise -> cash.

    No short selling is assumed.
    """
    predictions = pd.to_numeric(
        predictions,
        errors="coerce",
    )

    signal = (
        predictions > threshold
    ).astype(float)

    return signal


# =========================================================
# STRATEGY COMPARISON
# =========================================================


def compare_strategies(
    prices,
    ml_predictions,
    transaction_cost_bps=5.0,
    slippage_bps=5.0,
    sma_period=200,
    prediction_threshold=0.0,
):
    """
    Compare:

        ML strategy
        Buy and Hold
        SMA strategy

    All strategies use the same price period.
    """

    prices = pd.to_numeric(
        prices,
        errors="coerce",
    ).dropna()

    ml_predictions = pd.to_numeric(
        ml_predictions,
        errors="coerce",
    ).dropna()

    common_index = (
        prices.index.intersection(
            ml_predictions.index
        )
    )

    if len(common_index) < 2:
        raise ValueError(
            "Not enough overlapping price and prediction "
            "observations."
        )

    aligned_prices = prices.loc[
        common_index
    ]

    aligned_predictions = (
        ml_predictions.loc[
            common_index
        ]
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

    sma_signal = create_sma_signal(
        aligned_prices,
        period=sma_period,
    )

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