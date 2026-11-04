"""Offline research-only pipeline experiment on explicit restored test DB.

No market provider calls, no DB writes, and refuses to overwrite outputs.
"""
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone
from django.utils.dateparse import parse_date

from market_data.benchmark_data import load_cached_benchmark_prices, BenchmarkDataUnavailable
from market_data.management.commands.compare_forecast_feature_sets import prepare_paired_feature_sets
from market_data.models import HistoricalPrice
from market_data.research_pipeline_experiments import (
    add_volatility_normalized_features, evaluate_pipeline_grid,
)
from ml_engine import prepare_training_dataset
from stocks.models import Stock


def load_locked_cohort(path):
    """Require exactly 33 explicit symbols, not a guessed stock universe."""
    raw = Path(path).expanduser().read_bytes()
    manifest = json.loads(raw)
    symbols = manifest.get("symbols") if isinstance(manifest, dict) else None
    if not isinstance(symbols, list) or len(symbols) != 33:
        raise ValueError("Cohort manifest requires exactly 33 symbols.")
    if any(not isinstance(s, str) or not s or s != s.strip().upper() for s in symbols):
        raise ValueError("Invalid or unnormalized research symbol.")
    if len(set(symbols)) != 33:
        raise ValueError("Duplicate research symbol.")
    return symbols, hashlib.sha256(raw).hexdigest()


class Command(BaseCommand):
    help = "Research-only paired rolling-window/regularization/feature experiments."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--symbols", nargs="+")
        group.add_argument("--cohort-file", help='JSON: {"symbols": [exactly 33 tickers]}')
        parser.add_argument("--as-of", required=True)
        parser.add_argument("--horizon", type=int, choices=(1, 5, 20, 60), default=5)
        parser.add_argument("--min-train", type=int, default=500)
        parser.add_argument("--test-size", type=int, default=100)
        parser.add_argument("--windows", nargs="+", default=["expanding", "500", "750"])
        parser.add_argument("--alphas", nargs="+", type=int, default=[100, 300, 1000])
        parser.add_argument("--include-market", action="store_true",
                            help="Requires same-market locally cached benchmark, no fallback/download.")
        parser.add_argument("--output", required=True)

    def handle(self, *args, **opts):
        name = "marketpulse_restored_test"
        if os.environ.get("DB_NAME") != name or connection.settings_dict.get("NAME") != name:
            raise CommandError("Refusing research outside explicit marketpulse_restored_test.")
        cutoff = parse_date(opts["as_of"])
        if cutoff is None or cutoff > timezone.localdate():
            raise CommandError("--as-of must be a valid nonfuture YYYY-MM-DD.")
        horizon, min_train, test_size = opts["horizon"], opts["min_train"], opts["test_size"]
        if min_train < 300 or test_size < 30 or test_size < horizon + 2:
            raise CommandError("Require min-train>=300, test-size>=30 and test-size>=horizon+2.")
        try:
            windows = tuple(None if w == "expanding" else int(w) for w in opts["windows"])
        except ValueError as exc:
            raise CommandError("Invalid rolling training window.") from exc
        if len(set(windows)) != len(windows) or any(w is not None and w < min_train for w in windows):
            raise CommandError("Rolling windows must be unique and >= min-train.")
        alphas = tuple(opts["alphas"])
        if not alphas or len(set(alphas)) != len(alphas) or any(a not in (100, 300, 1000) for a in alphas):
            raise CommandError("Only unique alpha values 100, 300, 1000 are permitted.")
        fingerprint = None
        if opts["cohort_file"]:
            try:
                symbols, fingerprint = load_locked_cohort(opts["cohort_file"])
            except (ValueError, OSError) as exc:
                raise CommandError(str(exc)) from exc
        else:
            symbols = [s.strip().upper() for s in opts["symbols"]]
            if not 1 <= len(symbols) <= 33 or len(set(symbols)) != len(symbols):
                raise CommandError("Require 1–33 unique development symbols.")
        destination = Path(opts["output"]).expanduser().resolve()
        if destination.exists():
            raise CommandError("Refusing to overwrite an existing research report.")
        stocks = list(Stock.objects.filter(symbol__in=symbols, is_active=True).order_by("symbol"))
        if len(stocks) != len(symbols):
            raise CommandError("Some selected stocks are missing or inactive.")

        report = {
            "as_of": cutoff.isoformat(), "research_only": True, "read_only": True,
            "database": name, "horizon": horizon, "min_train": min_train,
            "test_size": test_size,
            "windows": ["expanding" if w is None else w for w in windows],
            "alphas": list(alphas), "market_aligned": opts["include_market"],
            "cohort_sha256": fingerprint, "symbols": symbols,
            "dataset_role": "development_diagnostic_not_independent_holdout",
            "method": "fixed, identical OOS fold origins with H+1 purged label gap",
            "stocks": [], "trading_approved": False,
        }
        for stock in stocks:
            row = {"symbol": stock.symbol, "status": "unavailable"}
            try:
                prices = list(HistoricalPrice.objects.filter(
                    stock=stock, date__lte=cutoff,
                ).order_by("date").values(
                    "date", "open_price", "high_price", "low_price",
                    "close_price", "volume", "is_ohlc_valid", "is_volume_valid",
                ))
                if len(prices) < min_train + test_size + horizon + 2:
                    raise ValueError("Insufficient stored prices.")
                frame = pd.DataFrame(prices)
                if opts["include_market"]:
                    benchmark = load_cached_benchmark_prices(frame, stock.exchange)
                    price_X, market_X, y = prepare_paired_feature_sets(frame, benchmark, horizon=horizon)
                    feature_sets = {"price_volume": price_X, "market_aligned": market_X}
                else:
                    price_X, y = prepare_training_dataset(frame, horizon=horizon)
                    feature_sets = {"price_volume": price_X}
                for key, X in tuple(feature_sets.items()):
                    feature_sets[f"{key}_volatility_normalized"] = add_volatility_normalized_features(X)
                row.update(evaluate_pipeline_grid(
                    feature_sets, y, horizon=horizon, min_train=min_train,
                    test_size=test_size, windows=windows, alphas=alphas,
                ))
                row["status"] = "evaluated"
                self.stdout.write(f'{stock.symbol}: {len(row["candidates"])} paired candidates')
            except (ValueError, TypeError, ArithmeticError, BenchmarkDataUnavailable) as exc:
                row["reason"] = str(exc)
                self.stderr.write(f"{stock.symbol}: unavailable ({exc})")
            report["stocks"].append(row)
        report["summary"] = {
            "evaluated_stocks": sum(row["status"] == "evaluated" for row in report["stocks"]),
            "model_promotion_approved": False,
            "note": "A separate untouched holdout and prospective outcomes are required.",
        }
        if not report["summary"]["evaluated_stocks"]:
            raise CommandError("No stock produced enough valid observations.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
        self.stdout.write(f"Saved report: {destination}")
