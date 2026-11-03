"""Read-only preview of stored adjusted-close factors versus Yahoo repair modes.

DOES NOT ingest, replace, save, or repair historical prices. Only operates
on the explicit restored test database; Yahoo requests are in memory.
"""

import math
import os
from datetime import date

import pandas as pd
import yfinance as yf
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from market_data.models import HistoricalPrice
from stocks.models import Stock


RESTORED_DB = "marketpulse_restored_test"
DEFAULT_TOLERANCE = 0.01  # 1% relative difference in adjusted/close ratio
DEFAULT_JUMP = 0.10       # 10% relative change between successive factors


def factor_from_prices(close, adjusted):
    """Currency-invariant adjusted/close ratio; reject invalid numbers."""
    try:
        close = float(close)
        adjusted = float(adjusted)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(close) or not math.isfinite(adjusted):
        return None
    if close <= 0 or adjusted <= 0:
        return None
    return adjusted / close


def provider_adjustment_factors(frame):
    """Convert Yahoo's timezone-aware daily index to a date->factor map."""
    if frame is None or frame.empty:
        raise ValueError("Provider returned no history")
    if "Close" not in frame.columns or "Adj Close" not in frame.columns:
        raise ValueError("Provider history lacks Close or Adj Close")
    factors = {}
    repaired_days = 0
    for idx, row in frame.iterrows():
        stamp = pd.Timestamp(idx)
        when = stamp.date()
        if when in factors:
            raise ValueError(f"Duplicate provider date: {when}")
        ratio = factor_from_prices(row["Close"], row["Adj Close"])
        if ratio is None:
            continue
        factors[when] = ratio
        if "Repaired?" in frame.columns and bool(row["Repaired?"]):
            repaired_days += 1
    if not factors:
        raise ValueError("Provider returned no valid adjustment factors")
    return factors, repaired_days


def compare_factors(reference, candidate, *, tolerance=DEFAULT_TOLERANCE,
                    max_examples=5):
    """Check relative differences on shared dates; never alter either input."""
    shared = sorted(set(reference) & set(candidate))
    mismatches = []
    max_gap = 0.0
    mismatch_count = 0
    for when in shared:
        base = reference[when]
        other = candidate[when]
        if base <= 0 or other <= 0:
            continue
        gap = abs(other / base - 1)
        max_gap = max(max_gap, gap)
        if gap >= tolerance:
            mismatch_count += 1
            if len(mismatches) < max_examples:
                mismatches.append({
                    "date": when.isoformat(),
                    "reference_factor": round(base, 6),
                    "candidate_factor": round(other, 6),
                    "difference_percent": round(100 * (other / base - 1), 2),
                })
    return {
        "shared_dates": len(shared),
        "mismatch_count": mismatch_count,
        "max_relative_difference_percent": round(100 * max_gap, 2),
        "examples": mismatches,
    }


def find_factor_jumps(factors, *, threshold=DEFAULT_JUMP, max_examples=5):
    """Detect relative day-to-day changes, not proof of a data error."""
    last = None
    events = []
    total = 0
    for when, factor in sorted(factors.items()):
        if factor <= 0:
            continue
        if last is not None:
            change = factor / last - 1
            if abs(change) >= threshold:
                total += 1
                if len(events) < max_examples:
                    events.append({
                        "date": when.isoformat(),
                        "relative_change_percent": round(100 * change, 2),
                    })
        last = factor
    return {"count": total, "examples": events}


class Command(BaseCommand):
    help = (
        "Read-only preview comparing stored adjusted/close ratios against "
        "Yahoo history(repair=False) and history(repair=True). "
        "Refuses databases other than marketpulse_restored_test."
    )

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="+", required=True)
        parser.add_argument("--period", default="10y")
        parser.add_argument("--timeout", type=float, default=30.0)
        parser.add_argument("--factor-tolerance-pct", type=float, default=1.0)
        parser.add_argument("--jump-threshold-pct", type=float, default=10.0)

    def handle(self, *args, **opts):
        if (os.environ.get("DB_NAME") != RESTORED_DB
                or connection.settings_dict.get("NAME") != RESTORED_DB):
            raise CommandError(
                "Read-only preview requires explicit "
                "DB_NAME=marketpulse_restored_test."
            )
        if opts["timeout"] <= 0:
            raise CommandError("--timeout must be positive.")
        tolerance = opts["factor_tolerance_pct"] / 100.0
        jump = opts["jump_threshold_pct"] / 100.0
        if not (0 < tolerance < 1 and 0 < jump < 1):
            raise CommandError("Factor thresholds must be between 0 and 100%.")
        symbols = list(dict.fromkeys(
            x.strip().upper() for x in opts["symbols"] if x.strip()
        ))
        if not 1 <= len(symbols) <= 10:
            raise CommandError("Supply between 1 and 10 symbols.")
        stocks = {
            item.symbol: item for item in
            Stock.objects.filter(symbol__in=symbols, is_active=True)
        }
        if len(stocks) != len(symbols):
            raise CommandError("One or more stocks are unknown or inactive.")

        self.stdout.write(
            "READ-ONLY PREVIEW: no historical prices are saved or updated."
        )
        self.stdout.write(
            "Factor differences are review flags; corporate actions, Yahoo "
            "repair behavior and provider revisions may legitimately differ."
        )
        completed = 0
        for symbol in symbols:
            stock = stocks[symbol]
            saved_rows = list(
                HistoricalPrice.objects.filter(stock=stock)
                .order_by("date")
                .values("date", "close_price", "adjusted_close")
            )
            stored = {}
            for row in saved_rows:
                ratio = factor_from_prices(
                    row["close_price"], row["adjusted_close"]
                )
                if ratio is not None:
                    stored[row["date"]] = ratio

            ticker = yf.Ticker(symbol)
            provider = {}
            try:
                for repaired in (False, True):
                    frame = ticker.history(
                        period=opts["period"],
                        auto_adjust=False,
                        repair=repaired,
                        timeout=opts["timeout"],
                    )
                    provider[repaired] = provider_adjustment_factors(frame)
            except (ValueError, TypeError, RuntimeError, KeyError) as exc:
                self.stderr.write(
                    f"{symbol}: provider comparison skipped: {exc}"
                )
                continue

            plain, _ = provider[False]
            repaired, marked = provider[True]
            stored_plain = compare_factors(
                stored, plain, tolerance=tolerance
            )
            stored_repaired = compare_factors(
                stored, repaired, tolerance=tolerance
            )
            mode_delta = compare_factors(
                plain, repaired, tolerance=tolerance
            )
            stored_jumps = find_factor_jumps(stored, threshold=jump)
            repaired_jumps = find_factor_jumps(repaired, threshold=jump)
            completed += 1
            self.stdout.write(
                f"{symbol}: stored={len(stored)} valid factors; "
                f"provider normal={len(plain)}, repaired={len(repaired)}; "
                f"Yahoo Repaired? rows={marked}"
            )
            self.stdout.write(
                f"  Stored vs repair=False: "
                f"{stored_plain['mismatch_count']}/"
                f"{stored_plain['shared_dates']} mismatches >= "
                f"{opts['factor_tolerance_pct']:g}%"
            )
            self.stdout.write(
                f"  Stored vs repair=True:  "
                f"{stored_repaired['mismatch_count']}/"
                f"{stored_repaired['shared_dates']} mismatches >= "
                f"{opts['factor_tolerance_pct']:g}%"
            )
            self.stdout.write(
                f"  repair=False vs repair=True: "
                f"{mode_delta['mismatch_count']}/"
                f"{mode_delta['shared_dates']} provider-mode differences"
            )
            self.stdout.write(
                f"  Stored factor jumps >= {opts['jump_threshold_pct']:g}%: "
                f"{stored_jumps['count']}; current repaired-provider jumps: "
                f"{repaired_jumps['count']}"
            )
            for label, report in (
                ("stored jump", stored_jumps),
                ("stored vs unrepaired", stored_plain),
                ("stored vs repaired", stored_repaired),
            ):
                for item in report["examples"][:3]:
                    self.stdout.write(f"    {label}: {item}")
            if not stored_plain["shared_dates"] or not stored_repaired["shared_dates"]:
                self.stderr.write(
                    f"  CAUTION: {symbol} lacks overlapping provider dates."
                )
        self.stdout.write(
            f"RESULT: {completed}/{len(symbols)} stocks compared; "
            "zero database writes."
        )
        if not completed:
            raise CommandError("Provider data unavailable for every stock.")
