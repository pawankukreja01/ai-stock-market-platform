"""Market-specific benchmark retrieval with a persistent local cache.

The cache makes repeated historical evaluations reproducible and avoids
re-downloading a benchmark when the requested date range is already present.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from stocks.catalog import market_for_exchange

logger = logging.getLogger(__name__)

BENCHMARK_TICKERS = {
    "US": "^GSPC",  # S&P 500
    "UK": "^FTSE",  # FTSE 100
}
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "benchmarks"
DEFAULT_DOWNLOAD_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 0.5


class BenchmarkDataUnavailable(RuntimeError):
    """Raised when a reproducible benchmark range cannot be provided."""


def _empty_series(status, ticker=None, reason=None):
    result = pd.Series(dtype=float)
    result.attrs.update({
        "status": status,
        "ticker": ticker,
        "reason": reason,
        "source": "none",
        "cache_hit": False,
    })
    return result


def _normalise_series(series):
    if series is None or len(series) == 0:
        return pd.Series(dtype=float)
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return pd.Series(dtype=float)
    try:
        index = pd.DatetimeIndex(pd.to_datetime(values.index, errors="coerce"))
        valid = ~index.isna()
        values = pd.Series(values.to_numpy()[valid], index=index[valid], dtype=float)
        if values.index.tz is not None:
            values.index = values.index.tz_localize(None)
        values.index = values.index.normalize()
        values = values[~values.index.duplicated(keep="last")].sort_index()
        return values
    except Exception:
        return pd.Series(dtype=float)


def _cache_paths(ticker, cache_dir=None):
    directory = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    safe_ticker = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(ticker)).strip("._") or "benchmark"
    csv_path = directory / f"{safe_ticker}.csv"
    return csv_path, csv_path.with_suffix(".json")


def _read_cache(csv_path):
    if not csv_path.exists():
        return pd.Series(dtype=float)
    try:
        frame = pd.read_csv(csv_path, parse_dates=["date"])
        if "date" not in frame.columns or "close" not in frame.columns:
            return pd.Series(dtype=float)
        series = pd.Series(
            pd.to_numeric(frame["close"], errors="coerce").to_numpy(),
            index=pd.DatetimeIndex(pd.to_datetime(frame["date"], errors="coerce")),
            dtype=float,
        )
        return _normalise_series(series)
    except Exception as exc:
        logger.warning("Could not read benchmark cache %s: %s", csv_path, exc)
        return pd.Series(dtype=float)


def _read_metadata(metadata_path):
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _metadata_covers(metadata, start_date, end_date):
    try:
        covered_start = pd.Timestamp(metadata["covered_start"]).normalize()
        covered_end = pd.Timestamp(metadata["covered_end"]).normalize()
        return covered_start <= start_date and covered_end >= end_date
    except (KeyError, TypeError, ValueError):
        return False


def _save_cache(csv_path, metadata_path, series, ticker, start_date, end_date, old_metadata):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    series = _normalise_series(series)
    if series.empty:
        raise ValueError("Refusing to save an empty benchmark series.")

    # Atomic replacement prevents an interrupted process from leaving a half-written CSV.
    csv_tmp = csv_path.with_suffix(".csv.tmp")
    series.rename("close").to_frame().rename_axis("date").to_csv(csv_tmp)
    csv_tmp.replace(csv_path)

    try:
        old_start = pd.Timestamp(old_metadata["covered_start"]).normalize()
        covered_start = min(old_start, start_date)
    except (KeyError, TypeError, ValueError):
        covered_start = start_date
    try:
        old_end = pd.Timestamp(old_metadata["covered_end"]).normalize()
        covered_end = max(old_end, end_date)
    except (KeyError, TypeError, ValueError):
        covered_end = end_date

    metadata = {
        "ticker": ticker,
        "covered_start": covered_start.date().isoformat(),
        "covered_end": covered_end.date().isoformat(),
        "updated_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    metadata_tmp = metadata_path.with_suffix(".json.tmp")
    metadata_tmp.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    metadata_tmp.replace(metadata_path)


def fetch_benchmark_prices(
    price_df,
    exchange="",
    *,
    strict=False,
    cache_dir=None,
    download_attempts=DEFAULT_DOWNLOAD_ATTEMPTS,
    retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
):
    """Fetch/cache benchmark prices for a stock's date range.

    A complete local cache is returned without network access. In non-strict
    (live-prediction) mode, an unavailable/incomplete benchmark returns an empty
    series, preserving the existing optional-feature fallback and logging the
    reason. In strict (backtest) mode, a cache miss that cannot be filled raises
    ``BenchmarkDataUnavailable`` rather than silently evaluating with a different
    feature set.
    """
    if price_df is None or getattr(price_df, "empty", True):
        return _empty_series("empty_request", reason="Price history is empty.")
    if "date" not in price_df.columns:
        return _empty_series("invalid_request", reason="Price history has no date column.")

    try:
        start_date = pd.to_datetime(price_df["date"].min()).normalize()
        end_date = pd.to_datetime(price_df["date"].max()).normalize()
    except (TypeError, ValueError) as exc:
        return _empty_series("invalid_request", reason=f"Invalid price-history dates: {exc}")
    if pd.isna(start_date) or pd.isna(end_date) or end_date < start_date:
        return _empty_series("invalid_request", reason="Invalid price-history date range.")

    market = market_for_exchange(exchange)
    ticker = BENCHMARK_TICKERS.get(str(market or "").strip().upper())
    if not ticker:
        reason = f"No benchmark mapping is configured for exchange {exchange!r}."
        logger.warning(reason)
        if strict:
            raise BenchmarkDataUnavailable(reason)
        return _empty_series("unsupported_exchange", reason=reason)

    if isinstance(download_attempts, bool) or not isinstance(download_attempts, int) or download_attempts < 1:
        raise ValueError("download_attempts must be a positive integer.")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds cannot be negative.")

    csv_path, metadata_path = _cache_paths(ticker, cache_dir)
    cached = _read_cache(csv_path)
    metadata = _read_metadata(metadata_path)
    if not cached.empty and _metadata_covers(metadata, start_date, end_date):
        cached.attrs.update({
            "status": "cache_hit",
            "ticker": ticker,
            "source": "local_cache",
            "cache_hit": True,
            "covered_start": metadata.get("covered_start"),
            "covered_end": metadata.get("covered_end"),
        })
        return cached

    end_exclusive = end_date + timedelta(days=2)
    last_error = None
    downloaded = pd.Series(dtype=float)
    for attempt in range(1, download_attempts + 1):
        try:
            history = yf.Ticker(ticker).history(
                start=start_date.date().isoformat(),
                end=end_exclusive.date().isoformat(),
                auto_adjust=False,
                actions=False,
            )
            if history is None or history.empty or "Close" not in history.columns:
                raise ValueError("Benchmark provider returned no usable Close prices.")
            downloaded = _normalise_series(history["Close"])
            if downloaded.empty:
                raise ValueError("Benchmark provider returned no valid closing prices.")
            # Reject truncated responses rather than marking the entire requested range cached.
            tolerance = pd.Timedelta(days=7)
            if downloaded.index.min() > start_date + tolerance or downloaded.index.max() < end_date - tolerance:
                raise ValueError(
                    f"Provider returned incomplete coverage ({downloaded.index.min().date()} to "
                    f"{downloaded.index.max().date()}) for requested range "
                    f"{start_date.date()} to {end_date.date()}."
                )
            break
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Benchmark download attempt %s/%s failed for %s: %s",
                attempt, download_attempts, ticker, exc,
            )
            if attempt < download_attempts and retry_delay_seconds:
                time.sleep(retry_delay_seconds * attempt)

    if downloaded.empty:
        reason = (
            f"Benchmark cache miss for {ticker} ({start_date.date()} to {end_date.date()}); "
            f"download failed after {download_attempts} attempt(s): {last_error}"
        )
        if strict:
            raise BenchmarkDataUnavailable(reason) from last_error
        logger.warning("%s; omitting optional benchmark features for this request.", reason)
        result = _empty_series("download_failed", ticker=ticker, reason=reason)
        return result

    merged = pd.concat([cached, downloaded]) if not cached.empty else downloaded.copy()
    merged = _normalise_series(merged)
    _save_cache(csv_path, metadata_path, merged, ticker, start_date, end_date, metadata)
    saved_metadata = _read_metadata(metadata_path)
    merged.attrs.update({
        "status": "downloaded_and_cached",
        "ticker": ticker,
        "source": "download_and_local_cache",
        "cache_hit": False,
        "covered_start": saved_metadata.get("covered_start"),
        "covered_end": saved_metadata.get("covered_end"),
    })
    return merged
