import math

import numpy as np
import pandas as pd
import yfinance as yf


TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.0
VAR_CONFIDENCE = 0.95


def _clean_series(series):
    """
    Convert a pandas Series to numeric values and remove invalid values.
    """
    return pd.to_numeric(series, errors="coerce").dropna()


def calculate_daily_returns(prices):
    """
    Calculate percentage daily returns from a price series.
    """
    prices = _clean_series(prices)

    if len(prices) < 2:
        return pd.Series(dtype=float)

    returns = prices.pct_change().dropna()

    return returns.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()


def calculate_annualised_volatility(returns):
    """
    Annualised volatility based on daily returns.
    """
    returns = _clean_series(returns)

    if len(returns) < 2:
        return None

    return float(
        returns.std(ddof=1)
        * math.sqrt(TRADING_DAYS_PER_YEAR)
    )


def calculate_maximum_drawdown(prices):
    """
    Calculate the largest peak-to-trough decline.
    """
    prices = _clean_series(prices)

    if len(prices) < 2:
        return None

    running_max = prices.cummax()

    drawdowns = (
        prices / running_max
    ) - 1.0

    if drawdowns.empty:
        return None

    return float(drawdowns.min())


def _align_returns(
    stock_returns,
    benchmark_returns,
):
    """
    Align stock and benchmark returns by calendar date.

    Yahoo Finance benchmark data can contain timezone-aware
    timestamps while database stock data uses date values.

    Both indexes are normalised to timezone-naive calendar
    dates before matching.
    """
    stock = _clean_series(
        stock_returns
    ).copy()

    benchmark = _clean_series(
        benchmark_returns
    ).copy()

    stock.index = (
        pd.to_datetime(
            stock.index
        )
        .tz_localize(None)
        .normalize()
    )

    benchmark.index = (
        pd.to_datetime(
            benchmark.index
        )
        .tz_localize(None)
        .normalize()
    )

    combined = pd.concat(
        [
            stock.rename("stock"),
            benchmark.rename("benchmark"),
        ],
        axis=1,
        join="inner",
    ).dropna()

    return combined


def calculate_beta(
    stock_returns,
    benchmark_returns,
):
    """
    Calculate beta:

        Cov(stock, benchmark)
        ---------------------
        Var(benchmark)
    """
    combined = _align_returns(
        stock_returns,
        benchmark_returns,
    )

    if len(combined) < 2:
        return None

    benchmark_variance = (
        combined["benchmark"].var(
            ddof=1
        )
    )

    if (
        benchmark_variance == 0
        or pd.isna(benchmark_variance)
    ):
        return None

    covariance = combined[
        "stock"
    ].cov(
        combined["benchmark"]
    )

    if pd.isna(covariance):
        return None

    return float(
        covariance
        / benchmark_variance
    )


def calculate_sharpe_ratio(
    returns,
    risk_free_rate=RISK_FREE_RATE,
):
    """
    Calculate annualised Sharpe ratio.

    The supplied risk-free rate is annualised and converted
    to an equivalent daily rate.
    """
    returns = _clean_series(
        returns
    )

    if len(returns) < 2:
        return None

    daily_risk_free_rate = (
        (1 + risk_free_rate)
        ** (1 / TRADING_DAYS_PER_YEAR)
    ) - 1

    excess_returns = (
        returns
        - daily_risk_free_rate
    )

    volatility = (
        excess_returns.std(
            ddof=1
        )
    )

    if (
        volatility == 0
        or pd.isna(volatility)
    ):
        return None

    return float(
        (
            excess_returns.mean()
            / volatility
        )
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_downside_deviation(
    returns,
    minimum_acceptable_return=RISK_FREE_RATE,
):
    """
    Calculate annualised downside deviation.

    Only returns below the minimum acceptable return
    contribute to downside risk.
    """
    returns = _clean_series(
        returns
    )

    if len(returns) < 2:
        return None

    daily_mar = (
        (1 + minimum_acceptable_return)
        ** (1 / TRADING_DAYS_PER_YEAR)
    ) - 1

    downside = (
        returns[
            returns < daily_mar
        ]
        - daily_mar
    )

    if downside.empty:
        return 0.0

    downside_squared = (
        downside ** 2
    )

    return float(
        math.sqrt(
            downside_squared.mean()
        )
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_sortino_ratio(
    returns,
    risk_free_rate=RISK_FREE_RATE,
):
    """
    Calculate annualised Sortino ratio.
    """
    returns = _clean_series(
        returns
    )

    if len(returns) < 2:
        return None

    daily_risk_free_rate = (
        (1 + risk_free_rate)
        ** (1 / TRADING_DAYS_PER_YEAR)
    ) - 1

    excess_returns = (
        returns
        - daily_risk_free_rate
    )

    downside = (
        returns[
            returns < daily_risk_free_rate
        ]
        - daily_risk_free_rate
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
        or pd.isna(downside_deviation)
    ):
        return None

    return float(
        (
            excess_returns.mean()
            / downside_deviation
        )
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_var(
    returns,
    confidence=VAR_CONFIDENCE,
):
    """
    Calculate historical Value at Risk.

    For 95% confidence, this returns the 5th percentile
    of historical daily returns.
    """
    returns = _clean_series(
        returns
    )

    if returns.empty:
        return None

    percentile = (
        1 - confidence
    )

    return float(
        returns.quantile(
            percentile
        )
    )


def calculate_expected_shortfall(
    returns,
    confidence=VAR_CONFIDENCE,
):
    """
    Calculate historical Expected Shortfall (CVaR).

    This is the average return of observations that are
    at or below the VaR threshold.
    """
    returns = _clean_series(
        returns
    )

    if returns.empty:
        return None

    var = calculate_var(
        returns,
        confidence=confidence,
    )

    if var is None:
        return None

    tail_returns = returns[
        returns <= var
    ]

    if tail_returns.empty:
        return None

    return float(
        tail_returns.mean()
    )


def calculate_benchmark_correlation(
    stock_returns,
    benchmark_returns,
):
    """
    Calculate Pearson correlation between stock and
    benchmark daily returns.
    """
    combined = _align_returns(
        stock_returns,
        benchmark_returns,
    )

    if len(combined) < 2:
        return None

    correlation = combined[
        "stock"
    ].corr(
        combined["benchmark"]
    )

    if pd.isna(correlation):
        return None

    return float(correlation)


def calculate_loss_frequency(
    returns,
):
    """
    Calculate the percentage of trading days with
    a negative return.
    """
    returns = _clean_series(
        returns
    )

    if returns.empty:
        return None

    return float(
        (returns < 0).mean()
    )


def calculate_annualised_return(
    prices,
):
    """
    Calculate annualised return using the first and
    last available prices.
    """
    prices = _clean_series(
        prices
    )

    if len(prices) < 2:
        return None

    first_price = float(
        prices.iloc[0]
    )

    last_price = float(
        prices.iloc[-1]
    )

    if (
        first_price <= 0
        or last_price <= 0
    ):
        return None

    try:
        start_date = pd.Timestamp(
            prices.index[0]
        )

        end_date = pd.Timestamp(
            prices.index[-1]
        )

        number_of_days = (
            end_date - start_date
        ).days

    except Exception:
        return None

    if number_of_days <= 0:
        return None

    years = (
        number_of_days
        / 365.25
    )

    if years <= 0:
        return None

    return float(
        (
            last_price
            / first_price
        )
        ** (1 / years)
        - 1
    )


def calculate_risk_metrics(
    stock_prices,
    benchmark_prices=None,
    benchmark_symbol="^GSPC",
):
    """
    Calculate the complete risk profile for a stock.

    Parameters
    ----------
    stock_prices:
        Pandas Series containing stock closing prices.

    benchmark_prices:
        Optional Pandas Series containing benchmark
        closing prices.

    benchmark_symbol:
        Benchmark identifier.

    Returns
    -------
    dict
        Calculated risk metrics.
    """
    stock_prices = _clean_series(
        stock_prices
    )

    if len(stock_prices) < 2:
        raise ValueError(
            "At least two stock price observations "
            "are required."
        )

    stock_returns = (
        calculate_daily_returns(
            stock_prices
        )
    )

    result = {
        "annualised_volatility": (
            calculate_annualised_volatility(
                stock_returns
            )
        ),

        "maximum_drawdown": (
            calculate_maximum_drawdown(
                stock_prices
            )
        ),

        "sharpe_ratio": (
            calculate_sharpe_ratio(
                stock_returns
            )
        ),

        "sortino_ratio": (
            calculate_sortino_ratio(
                stock_returns
            )
        ),

        "downside_deviation": (
            calculate_downside_deviation(
                stock_returns
            )
        ),

        "var_95": (
            calculate_var(
                stock_returns,
                confidence=0.95,
            )
        ),

        "expected_shortfall_95": (
            calculate_expected_shortfall(
                stock_returns,
                confidence=0.95,
            )
        ),

        "historical_loss_frequency": (
            calculate_loss_frequency(
                stock_returns
            )
        ),

        "annualised_return": (
            calculate_annualised_return(
                stock_prices
            )
        ),

        "observations": int(
            len(stock_prices)
        ),

        "benchmark": benchmark_symbol,
    }

    if benchmark_prices is not None:
        benchmark_prices = _clean_series(
            benchmark_prices
        )

        benchmark_returns = (
            calculate_daily_returns(
                benchmark_prices
            )
        )

        result["beta"] = (
            calculate_beta(
                stock_returns,
                benchmark_returns,
            )
        )

        result[
            "benchmark_correlation"
        ] = (
            calculate_benchmark_correlation(
                stock_returns,
                benchmark_returns,
            )
        )

    else:
        result["beta"] = None

        result[
            "benchmark_correlation"
        ] = None

    return result


def fetch_benchmark_prices(
    benchmark_symbol,
    start_date,
    end_date,
):
    """
    Download benchmark closing prices from Yahoo Finance.
    """
    ticker = yf.Ticker(
        benchmark_symbol
    )

    history = ticker.history(
        start=start_date,
        end=end_date,
        auto_adjust=False,
        actions=False,
    )

    if history.empty:
        return pd.Series(
            dtype=float
        )

    return _clean_series(
        history["Close"]
    )