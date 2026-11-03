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
        prices.pct_change(1, fill_method=None)
    )

    for period in periods:
        if period == 1:
            continue

        result[
            f"return_{period}d"
        ] = prices.pct_change(period, fill_method=None)

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

    Handles edge cases explicitly:
    - No losses and positive gains: RSI = 100
    - No gains and positive losses: RSI = 0
    - No gains and no losses: RSI = 50

    Missing or insufficient observations remain NaN.
    """
    delta = prices.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    average_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    # Calculate relative strength where average loss is positive.
    relative_strength = average_gain.div(
        average_loss.where(average_loss.gt(0))
    )

    rsi = 100 - (100 / (1 + relative_strength))

    valid_averages = (
        average_gain.notna()
        & average_loss.notna()
    )

    # No losses: maximum RSI.
    no_losses = (
        valid_averages
        & average_loss.eq(0)
        & average_gain.gt(0)
    )

    rsi = rsi.mask(no_losses, 100.0)

    # No gains: minimum RSI.
    no_gains = (
        valid_averages
        & average_gain.eq(0)
        & average_loss.gt(0)
    )

    rsi = rsi.mask(no_gains, 0.0)

    # Completely unchanged prices: neutral RSI.
    no_movement = (
        valid_averages
        & average_gain.eq(0)
        & average_loss.eq(0)
    )

    rsi = rsi.mask(no_movement, 50.0)

    return rsi.clip(lower=0, upper=100)


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
            + ", ".join(missing_columns)
        )

    df = df.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    for column in required_columns:
        df[column] = _clean_numeric(df[column])

    # Open is optional for backwards compatibility with older DataFrame
    # callers. When supplied, it is part of OHLC candle validation.
    open_price = None
    if "open_price" in df.columns:
        df["open_price"] = _clean_numeric(df["open_price"])
        open_price = df["open_price"]

    close = df["close_price"]
    high = df["high_price"]
    low = df["low_price"]
    volume = df["volume"]

    def quality_flag_mask(column):
        """Treat absent flags as legacy/unknown; treat null/false as invalid."""
        if column not in df.columns:
            return pd.Series(True, index=df.index, dtype=bool)
        accepted = {"true", "1", "yes", "y", "t"}
        return df[column].map(
            lambda value: str(value).strip().lower() in accepted
        ).astype(bool)

    # Reject invalid candle prices before calculating price-based features.
    valid_feature_price_rows = (
        np.isfinite(close)
        & np.isfinite(high)
        & np.isfinite(low)
        & close.gt(0)
        & high.gt(0)
        & low.gt(0)
        & high.ge(low)
        & high.ge(close)
        & low.le(close)
        & quality_flag_mask("is_ohlc_valid")
    )

    # When Open is available, it must be finite, positive and inside the
    # candle's high/low range. A missing Open therefore invalidates that row.
    if open_price is not None:
        valid_feature_price_rows &= (
            np.isfinite(open_price)
            & open_price.gt(0)
            & high.ge(open_price)
            & low.le(open_price)
        )

    # Invalid OHLC rows must not contaminate rolling price calculations,
    # returns, ATR values or future-return target paths.
    close = close.where(valid_feature_price_rows)
    high = high.where(valid_feature_price_rows)
    low = low.where(valid_feature_price_rows)

    # Invalid volume affects volume-derived features, but does not invalidate
    # an otherwise valid OHLC observation or its close-based features.
    valid_feature_volume_rows = (
        np.isfinite(volume)
        & volume.ge(0)
        & quality_flag_mask("is_volume_valid")
    )
    volume = volume.where(valid_feature_volume_rows)

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
                    12,
                    fill_method=None,
                )
            ),
        },
        index=df.index,
    )

    # ---------------------------------------------------------
    # Volatility
    # ---------------------------------------------------------

    daily_returns = close.pct_change(fill_method=None)

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
                volume.pct_change(fill_method=None)
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

                    # Stock performance in excess of its market benchmark.
                    # All values use data available through the same date only.
                    for period in (1, 5, 20, 60):
                        stock_return = close.pct_change(
                            periods=period,
                            fill_method=None,
                        )
                        market_return = aligned_benchmark.pct_change(
                            periods=period,
                            fill_method=None,
                        )
                        if stock_return.notna().any() and market_return.notna().any():
                            benchmark_features[f"relative_return_{period}d"] = (
                                stock_return - market_return
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
        # Features are known at close t. The model is executed at close t+1,
        # so its target is the H-session return from that entry close through
        # close t+H+1 (not the return beginning at the signal close).
        target = (
            close.shift(-(horizon + 1))
            / close.shift(-1)
        ) - 1

        # Require every OHLC-valid close from signal date t through the
        # executable entry/exit path t+1 ... t+H+1.
        path_length = horizon + 2
        valid_path = (
            valid_feature_price_rows.astype("int64")
            .rolling(window=path_length, min_periods=path_length)
            .sum()
            .shift(-(path_length - 1))
            .eq(path_length)
        )

        features[f"target_{horizon}d"] = target.where(valid_path)

    # An invalid candle cannot be used as a model input row.
    features.loc[~valid_feature_price_rows, :] = np.nan

    return features


def prepare_training_dataset(
    prices,
    benchmark_prices=None,
    horizon=5,
):
    """
    Build a leakage-safe training dataset.

    The target represents the requested number of daily returns after
    next-session-close execution: C[t + H + 1] / C[t + 1] - 1.

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


def prepare_latest_feature_row(
    prices,
    benchmark_prices=None,
):
    """
    Build the latest complete feature row for a current forecast.

    Unlike the supervised training dataset, this row does not need
    a known future target. It must, however, contain every feature
    required by the model; incomplete latest features raise an error
    instead of silently falling back to an older date.
    """
    features = build_stock_features(
        prices,
        benchmark_prices=benchmark_prices,
    )

    if features.empty:
        raise ValueError(
            "Unable to build features from the supplied price history."
        )

    feature_columns = [
        column
        for column in features.columns
        if not column.startswith("target_")
    ]

    if not feature_columns:
        raise ValueError("No model features were generated.")

    latest = (
        features[feature_columns]
        .replace([np.inf, -np.inf], np.nan)
        .iloc[[-1]]
        .copy()
    )

    missing_columns = latest.columns[
        latest.isna().iloc[0]
    ].tolist()

    if missing_columns:
        raise ValueError(
            "The latest observation is missing usable feature values: "
            + ", ".join(missing_columns)
        )

    return latest
