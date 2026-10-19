import math

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


def _clean_numeric(series):
    """
    Convert a pandas Series to numeric values and
    remove invalid values.
    """
    return pd.to_numeric(
        series,
        errors="coerce",
    )


def calculate_returns(
    prices,
    periods=(1, 5, 20, 60, 126, 252),
):
    """
    Calculate historical percentage returns
    over multiple horizons.

    Returns are expressed as decimal values.

    Example:
        0.05 = +5%
        -0.03 = -3%
    """
    prices = _clean_numeric(prices)

    result = pd.DataFrame(
        index=prices.index
    )

    result["return_1d"] = (
        prices.pct_change(1)
    )

    for period in periods:
        if period == 1:
            continue

        result[
            f"return_{period}d"
        ] = prices.pct_change(period)

    return result


def calculate_sma(
    prices,
    period,
):
    """
    Simple moving average.
    """
    return prices.rolling(
        window=period,
        min_periods=period,
    ).mean()


def calculate_ema(
    prices,
    period,
):
    """
    Exponential moving average.
    """
    return prices.ewm(
        span=period,
        adjust=False,
        min_periods=period,
    ).mean()


def calculate_rsi(
    prices,
    period=14,
):
    """
    Wilder-style RSI calculation.
    """
    delta = prices.diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    average_gain = (
        gain.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()
    )

    average_loss = (
        loss.ewm(
            alpha=1 / period,
            adjust=False,
            min_periods=period,
        ).mean()
    )

    relative_strength = (
        average_gain
        / average_loss.replace(
            0,
            np.nan,
        )
    )

    rsi = (
        100
        - (
            100
            / (
                1
                + relative_strength
            )
        )
    )

    return rsi


def calculate_rolling_volatility(
    returns,
    period,
):
    """
    Annualised rolling volatility.
    """
    return (
        returns.rolling(
            window=period,
            min_periods=period,
        ).std()
        * math.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )


def calculate_relative_volume(
    volume,
    period=20,
):
    """
    Current volume divided by its rolling
    average volume.
    """
    average_volume = (
        volume.rolling(
            window=period,
            min_periods=period,
        ).mean()
    )

    return (
        volume
        / average_volume.replace(
            0,
            np.nan,
        )
    )


def calculate_atr(
    highs,
    lows,
    closes,
    period=14,
):
    """
    Average True Range using Wilder-style
    exponential smoothing.
    """
    previous_close = closes.shift(1)

    true_range = pd.concat(
        [
            highs - lows,
            (highs - previous_close).abs(),
            (lows - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    return atr


def build_stock_features(
    prices,
    benchmark_prices=None,
):
    """
    Build the ML feature matrix from stock prices.

    Parameters
    ----------
    prices:
        DataFrame containing:
            date
            open_price
            high_price
            low_price
            close_price
            volume

    benchmark_prices:
        Optional pandas Series indexed by date.

    Returns
    -------
    pandas.DataFrame
        Feature matrix indexed by date.
    """
    df = prices.copy()

    if df.empty:
        return pd.DataFrame()

    required_columns = [
        "high_price",
        "low_price",
        "close_price",
        "volume",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(
                missing_columns
            )
        )

    df = df.sort_values(
        "date"
    ).copy()

    df["date"] = pd.to_datetime(
        df["date"]
    )

    df = df.set_index(
        "date"
    )

    for column in required_columns:
        df[column] = _clean_numeric(
            df[column]
        )

    close = df["close_price"]
    high = df["high_price"]
    low = df["low_price"]
    volume = df["volume"]

    # ---------------------------------------------------------
    # Returns
    # ---------------------------------------------------------

    return_features = calculate_returns(
        close
    )

    # ---------------------------------------------------------
    # Moving averages
    # ---------------------------------------------------------

    sma20 = calculate_sma(
        close,
        20,
    )

    sma50 = calculate_sma(
        close,
        50,
    )

    sma200 = calculate_sma(
        close,
        200,
    )

    ema20 = calculate_ema(
        close,
        20,
    )

    ema50 = calculate_ema(
        close,
        50,
    )

    # ---------------------------------------------------------
    # Trend ratios
    # ---------------------------------------------------------

    trend_features = pd.DataFrame(
        {
            "sma20_ratio": (
                close / sma20
            ),
            "sma50_ratio": (
                close / sma50
            ),
            "sma200_ratio": (
                close / sma200
            ),
            "ema20_ratio": (
                close / ema20
            ),
            "ema50_ratio": (
                close / ema50
            ),
        },
        index=df.index,
    )

    # ---------------------------------------------------------
    # Momentum
    # ---------------------------------------------------------

    momentum_features = pd.DataFrame(
        {
            "rsi_14": calculate_rsi(
                close,
                14,
            ),
            "roc_12": (
                close.pct_change(
                    12
                )
            ),
        },
        index=df.index,
    )

    # ---------------------------------------------------------
    # Volatility
    # ---------------------------------------------------------

    daily_returns = close.pct_change()

    volatility_features = pd.DataFrame(
        {
            "volatility_20d": (
                calculate_rolling_volatility(
                    daily_returns,
                    20,
                )
            ),
            "volatility_60d": (
                calculate_rolling_volatility(
                    daily_returns,
                    60,
                )
            ),
            "atr_14_ratio": (
                calculate_atr(
                    high,
                    low,
                    close,
                    14,
                )
                / close
            ),
        },
        index=df.index,
    )

    # ---------------------------------------------------------
    # Volume
    # ---------------------------------------------------------

    volume_features = pd.DataFrame(
        {
            "volume_change_1d": (
                volume.pct_change()
            ),
            "relative_volume_20d": (
                calculate_relative_volume(
                    volume,
                    20,
                )
            ),
        },
        index=df.index,
    )

    # ---------------------------------------------------------
    # Benchmark features
    # ---------------------------------------------------------

    benchmark_features = pd.DataFrame(index=df.index)

    if benchmark_prices is not None:
        # A missing or unusable benchmark should not make every
        # stock observation unusable. These are optional features.
        benchmark = pd.to_numeric(
            benchmark_prices,
            errors="coerce",
        ).dropna().copy()

        if not benchmark.empty:
            benchmark_index = pd.DatetimeIndex(
                pd.to_datetime(benchmark.index)
            )

            if benchmark_index.tz is not None:
                benchmark_index = benchmark_index.tz_localize(None)

            benchmark.index = benchmark_index.normalize()
            benchmark = benchmark[
                ~benchmark.index.duplicated(keep="last")
            ].sort_index()

            stock_index = pd.DatetimeIndex(
                pd.to_datetime(df.index)
            )

            if stock_index.tz is not None:
                stock_index = stock_index.tz_localize(None)

            stock_dates = stock_index.normalize()
            aligned_benchmark = benchmark.reindex(stock_dates)
            aligned_benchmark.index = df.index

            # Use benchmark features only if coverage is sufficient.
            # Sparse/short benchmark data would otherwise remove most
            # rows when prepare_training_dataset() drops missing data.
            coverage = (
                float(aligned_benchmark.notna().mean())
                if len(aligned_benchmark)
                else 0.0
            )

            if (
                int(aligned_benchmark.notna().sum()) >= 21
                and coverage >= 0.80
            ):
                benchmark_return_1d = aligned_benchmark.pct_change(
                    periods=1,
                    fill_method=None,
                )
                benchmark_return_20d = aligned_benchmark.pct_change(
                    periods=20,
                    fill_method=None,
                )

                # Add both columns only when they contain valid data.
                if benchmark_return_1d.notna().any() and benchmark_return_20d.notna().any():
                    benchmark_features["benchmark_return_1d"] = (
                        benchmark_return_1d
                    )
                    benchmark_features["benchmark_return_20d"] = (
                        benchmark_return_20d
                    )

    # ---------------------------------------------------------
    # Combine features
    # ---------------------------------------------------------

    features = pd.concat(
        [
            return_features,
            trend_features,
            momentum_features,
            volatility_features,
            volume_features,
            benchmark_features,
        ],
        axis=1,
    )

    # ---------------------------------------------------------
    # Target variables
    #
    # These are deliberately future returns.
    # They are NOT included in the input features
    # used at prediction time.
    # ---------------------------------------------------------

    for horizon in [
        1,
        5,
        20,
        60,
        126,
        252,
    ]:
        features[
            f"target_{horizon}d"
        ] = (
            close.shift(-horizon)
            / close
        ) - 1

    return features


def prepare_training_dataset(
    prices,
    benchmark_prices=None,
    horizon=5,
):
    """
    Build a leakage-safe training dataset.

    The target represents the future return over
    the requested horizon.

    Rows with missing feature or target values
    are removed.
    """
    features = build_stock_features(
        prices,
        benchmark_prices=benchmark_prices,
    )

    target_column = (
        f"target_{horizon}d"
    )

    if target_column not in features.columns:
        raise ValueError(
            f"Unsupported horizon: {horizon}"
        )

    feature_columns = [
        column
        for column in features.columns
        if not column.startswith(
            "target_"
        )
    ]

    dataset = features[
        feature_columns
        + [target_column]
    ].copy()

    dataset = dataset.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    dataset = dataset.dropna()

    return (
        dataset[feature_columns],
        dataset[target_column],
    )