"""Paired, read-only forecast feature ablation on exactly matched dates.

Uses cached same-market benchmarks only, fixed model hyperparameters and the
same expanding-window purged splits. Research results on historical periods
that have already been inspected are NOT independent confirmation of skill.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.dateparse import parse_date

from market_data.benchmark_data import (
    BenchmarkDataUnavailable,
    load_cached_benchmark_prices,
)
from market_data.models import HistoricalPrice
from market_data.management.commands.validate_stock_forecasts import (
    MODEL_FACTORIES,
    build_model_scorecard,
    common_calendar_window,
)
from ml_engine import prepare_training_dataset
from ml_final_validation import build_final_validation_report
from backtesting import generate_walk_forward_predictions
from stocks.models import Stock
from walk_forward import describe_fold, generate_walk_forward_splits


EXPECTED_MARKET_COLUMNS = frozenset({
    "benchmark_return_1d", "benchmark_return_20d",
    "relative_return_1d", "relative_return_5d",
    "relative_return_20d", "relative_return_60d",
})
BASELINES = ("zero_return", "historical_mean", "momentum")
RESTORED_TEST_DB = "marketpulse_restored_test"


def prepare_paired_feature_sets(price_frame, benchmark_prices, *, horizon):
    """Align features and *verify identical targets* before any training.

    Pairing BEFORE fold generation ensures that training and test origins,
    target values, baseline returns and purge intervals are identical.
    """
    x_price, y_price = prepare_training_dataset(
        price_frame, horizon=horizon
    )
    x_market, y_market = prepare_training_dataset(
        price_frame, benchmark_prices=benchmark_prices, horizon=horizon
    )
    if not EXPECTED_MARKET_COLUMNS.issubset(x_market.columns):
        raise ValueError("Market-relative benchmark features are unavailable.")

    common_dates = x_price.index.intersection(x_market.index).sort_values()
    if len(common_dates) != len(common_dates.unique()):
        raise ValueError("Duplicate forecast date in paired feature sets.")
    if not len(common_dates):
        raise ValueError("No shared forecast dates for feature-set comparison.")

    x_price = x_price.loc[common_dates].copy()
    x_market = x_market.loc[common_dates].copy()
    y_price = y_price.loc[common_dates].copy()
    y_market = y_market.loc[common_dates].copy()

    if not x_price.index.equals(x_market.index):
        raise ValueError("Price and market feature dates differ.")
    if not y_price.index.equals(y_market.index):
        raise ValueError("Price and market target dates differ.")
    if not np.allclose(
        y_price.to_numpy(dtype=float),
        y_market.to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-12,
        equal_nan=False,
    ):
        raise ValueError("Inconsistent return targets across feature sets.")
    if not np.isfinite(y_price.to_numpy(dtype=float)).all():
        raise ValueError("Non-finite return target in aligned dataset.")

    return x_price, x_market, y_price


def evaluate_paired_feature_sets(
    price_features, market_features, y, *,
    model_factory, model_key, horizon, min_train, test_size,
):
    """Run both candidates with identical folds and identical OOS dates."""
    if not price_features.index.equals(market_features.index):
        raise ValueError("Paired evaluation requires identical feature dates.")
    if not price_features.index.equals(y.index):
        raise ValueError("Paired evaluation requires identical target dates.")
    folds = generate_walk_forward_splits(
        price_features,
        y,
        minimum_train_size=min_train,
        test_size=test_size,
        horizon=horizon,
        step_size=test_size,
    )
    if len(folds) < 2:
        raise ValueError("Fewer than two paired walk-forward test folds.")
    described = [describe_fold(price_features, fold) for fold in folds]
    reports = {}
    for name, X in (
        ("price_volume", price_features),
        ("market_aligned", market_features),
    ):
        predictions = generate_walk_forward_predictions(
            X, y, folds, model_factory
        )
        reports[name] = build_final_validation_report(
            X, y, described, predictions, model_key, horizon
        )

    first = reports["price_volume"]
    second = reports["market_aligned"]
    if (
        first["protocol"]["out_of_sample_observations"]
        != second["protocol"]["out_of_sample_observations"]
    ):
        raise ValueError("Paired experiments have different OOS sample counts.")
    for name in BASELINES:
        one = first["metrics"][name]
        two = second["metrics"][name]
        if one["observations"] != two["observations"]:
            raise ValueError("Baseline observation counts differ.")
        for metric in ("mae", "rmse", "directional_accuracy"):
            if one[metric] is None or two[metric] is None or not np.isclose(
                one[metric], two[metric], rtol=0.0, atol=1e-12,
            ):
                raise ValueError(
                    "Baseline metrics differ: experiments were not paired."
                )
    p_mae = first["metrics"]["selected_model"]["mae"]
    m_mae = second["metrics"]["selected_model"]["mae"]
    if p_mae is None or m_mae is None:
        raise ValueError("No comparable model MAE available.")
    return {
        "folds": len(folds),
        "out_of_sample_observations": first["protocol"]["out_of_sample_observations"],
        "oos_start_date": described[0].get("test_start_date"),
        "oos_end_date": described[-1].get("test_end_date"),
        "price_volume": build_model_scorecard(first),
        "market_aligned": build_model_scorecard(second),
        "market_mae_improvement_percentage_points": round(
            (p_mae - m_mae) * 100, 4
        ),
        "baseline_metrics": {
            name: first["metrics"][name] for name in BASELINES
        },
        "same_test_dates_and_targets": True,
        "historical_window_role": "development_diagnostic_not_final_holdout",
    }


class Command(BaseCommand):
    help = (
        "Compare price-only vs market-aligned features with identical "
        "training/test dates, offline cache only, on the restored test DB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols", nargs="+", required=True,
            help="Between 1 and 10 active stock symbols.",
        )
        parser.add_argument(
            "--model", choices=tuple(MODEL_FACTORIES),
            default="zero_anchor_ridge",
        )
        parser.add_argument("--horizon", type=int, default=5,
                            choices=(1, 5, 20, 60, 126, 252))
        parser.add_argument("--min-train", type=int, default=500)
        parser.add_argument("--test-size", type=int, default=100)
        parser.add_argument(
            "--as-of", required=True,
            help="Inclusive YYYY-MM-DD research cutoff.",
        )
        parser.add_argument(
            "--output",
            help="Write a new JSON report; refuses to overwrite existing files.",
        )

    def handle(self, *args, **options):
        if (
            os.environ.get("DB_NAME") != RESTORED_TEST_DB
            or connection.settings_dict.get("NAME") != RESTORED_TEST_DB
        ):
            raise CommandError(
                "Refusing to run paired research outside the explicit "
                "DB_NAME=marketpulse_restored_test database."
            )
        cutoff = parse_date(options["as_of"])
        if cutoff is None or cutoff > timezone.localdate():
            raise CommandError(
                "--as-of must be a valid YYYY-MM-DD not in the future."
            )
        horizon = options["horizon"]
        min_train = options["min_train"]
        test_size = options["test_size"]
        if min_train < 300 or test_size < 30 or test_size < horizon + 2:
            raise CommandError(
                "Require min-train>=300, test-size>=30 and test-size>=horizon+2."
            )

        tickers = list(dict.fromkeys(
            value.strip().upper() for value in options["symbols"]
            if value.strip()
        ))
        if not 1 <= len(tickers) <= 10:
            raise CommandError("Supply between 1 and 10 stock symbols.")
        stocks = list(
            Stock.objects.filter(symbol__in=tickers, is_active=True)
            .order_by("symbol")
        )
        if len(stocks) != len(tickers):
            raise CommandError("Unknown or inactive symbol.")

        bounds = [
            HistoricalPrice.objects.filter(
                stock=stock, date__lte=cutoff, close_price__gt=0,
            ).aggregate(first=Min("date"), last=Max("date"))
            for stock in stocks
        ]
        try:
            window_start, window_end = common_calendar_window(bounds)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        report = {
            "as_of": cutoff.isoformat(),
            "common_window": {
                "start": window_start.isoformat(),
                "end": window_end.isoformat(),
            },
            "source": "stored restored test database and local benchmark cache",
            "read_only": True,
            "market_benchmark_mode": "cache_only_no_provider_network",
            "protocol": (
                "Common feature-row dates, identical return targets and "
                "walk-forward folds with H+1-row purge; no shuffle."
            ),
            "model": options["model"],
            "horizon": horizon,
            "min_train": min_train,
            "test_size": test_size,
            "historical_window_role": (
                "development_diagnostic_not_independent_final_holdout"
            ),
            "stocks": [],
        }

        for stock in stocks:
            item = {"symbol": stock.symbol, "exchange": stock.exchange}
            try:
                rows = list(
                    HistoricalPrice.objects.filter(
                        stock=stock,
                        date__gte=window_start, date__lte=window_end,
                    ).order_by("date").values(
                        "date", "open_price", "high_price", "low_price",
                        "close_price", "volume", "is_ohlc_valid", "is_volume_valid",
                    )
                )
                if len(rows) < min_train + test_size + horizon + 2:
                    raise ValueError("Insufficient stored price history.")
                frame = pd.DataFrame(rows)
                benchmark = load_cached_benchmark_prices(
                    frame, stock.exchange
                )
                price_X, market_X, y = prepare_paired_feature_sets(
                    frame, benchmark, horizon=horizon
                )
                item["benchmark"] = benchmark.attrs.get("ticker")
                item["aligned_training_rows"] = len(y)
                item["price_feature_count"] = len(price_X.columns)
                item["market_feature_count"] = len(market_X.columns)
                item.update(evaluate_paired_feature_sets(
                    price_X, market_X, y,
                    model_factory=MODEL_FACTORIES[options["model"]],
                    model_key=options["model"],
                    horizon=horizon,
                    min_train=min_train,
                    test_size=test_size,
                ))
                item["status"] = "evaluated"
                delta = item["market_mae_improvement_percentage_points"]
                self.stdout.write(
                    f"{stock.symbol}: {item['folds']} paired folds / "
                    f"{item['out_of_sample_observations']} shared OOS dates; "
                    f"price-only MAE={item['price_volume']['mae_percent']:.3f}% "
                    f"market-aligned MAE={item['market_aligned']['mae_percent']:.3f}%; "
                    f"market feature improvement {delta:+.3f} pp"
                )
            except (
                BenchmarkDataUnavailable, ValueError, TypeError,
                ArithmeticError,
            ) as exc:
                item.update({
                    "status": "insufficient_or_invalid_data",
                    "reason": str(exc),
                })
                self.stderr.write(f"{stock.symbol}: skipped ({exc})")
            report["stocks"].append(item)

        evaluated = sum(
            item["status"] == "evaluated" for item in report["stocks"]
        )
        report["summary"] = {
            "evaluated_stocks": evaluated,
            "excluded_stocks": len(report["stocks"]) - evaluated,
            "ready_for_live_trading": False,
            "note": (
                "Paired historical comparison is diagnostic, not an "
                "independent final validation or proof of predictive skill."
            ),
        }
        self.stdout.write(
            f"RESULT: {evaluated}/{len(stocks)} stocks paired successfully."
        )

        if options.get("output"):
            destination = Path(options["output"]).expanduser().resolve()
            if destination.exists():
                raise CommandError(
                    f"Refusing to overwrite existing research report: {destination}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            self.stdout.write(f"Paired research report saved: {destination}")

        if not evaluated:
            raise CommandError("No stock had usable paired forecast history.")
