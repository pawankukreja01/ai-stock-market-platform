"""Read-only, reproducible multi-stock walk-forward research diagnostic.

This evaluates stored history, never places trades, never alters the database,
and intentionally does NOT declare a selected model investment-ready.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Min, Max
from django.utils import timezone

from stocks.models import Stock
from market_data.models import HistoricalPrice
from ml_engine import prepare_training_dataset
from market_data.benchmark_data import (
    load_cached_benchmark_prices, BenchmarkDataUnavailable,
)
from ml_models import (
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
)
from walk_forward import generate_walk_forward_splits, describe_fold
from backtesting import generate_walk_forward_predictions
from ml_final_validation import build_final_validation_report
from market_data.prediction_quality import assess_direction_bias


MODEL_FACTORIES = {
    "linear_regression": create_linear_regression_model,
    "random_forest": create_random_forest_model,
    "xgboost": create_xgboost_model,
}
HORIZONS = (1, 5, 20, 60, 126, 252)


def common_calendar_window(bounds):
    """Common inclusive calendar dates, without masking missing sessions."""
    if not bounds or any(
        item.get("first") is None or item.get("last") is None for item in bounds
    ):
        raise ValueError("Every stock needs dated historical prices.")
    start = max(item["first"] for item in bounds)
    end = min(item["last"] for item in bounds)
    if start >= end:
        raise ValueError("Selected stocks have no usable common calendar interval.")
    return start, end


def model_beats_all_baselines(report):
    """Require strictly lower MAE than every corresponding OOS baseline."""
    model_mae = report["metrics"]["selected_model"]["mae"]
    baselines = ("zero_return", "historical_mean", "momentum")
    return (
        model_mae is not None
        and all(
            report["metrics"][key]["mae"] is not None
            and model_mae < report["metrics"][key]["mae"]
            for key in baselines
        )
    )


def build_model_scorecard(report):
    """Summarize already-aligned out-of-sample returns in percentage points.

    This is diagnostic only. Choosing the best baseline here is descriptive,
    NOT an out-of-sample model-selection rule or a live trading recommendation.
    """
    metrics = report["metrics"]
    selected = metrics["selected_model"]
    baseline_names = ("zero_return", "historical_mean", "momentum")
    available = [
        (name, metrics[name]["mae"])
        for name in baseline_names
        if metrics[name].get("mae") is not None
    ]
    model_mae = selected.get("mae")
    best_name, best_mae = (
        min(available, key=lambda pair: pair[1]) if available else (None, None)
    )
    baselines_beaten = [
        name for name, mae in available
        if model_mae is not None and model_mae < mae
    ]
    return {
        "mae_percent": round(model_mae * 100, 4) if model_mae is not None else None,
        "best_baseline": best_name,
        "best_baseline_mae_percent": (
            round(best_mae * 100, 4) if best_mae is not None else None
        ),
        "mae_improvement_vs_best_baseline_percentage_points": (
            round((best_mae - model_mae) * 100, 4)
            if model_mae is not None and best_mae is not None
            else None
        ),
        "baselines_beaten_on_mae": baselines_beaten,
        "balanced_directional_accuracy_percent": (
            round(selected["balanced_directional_accuracy"] * 100, 2)
            if selected.get("balanced_directional_accuracy") is not None
            else None
        ),
        "negative_specificity_percent": (
            round(selected["negative_specificity"] * 100, 2)
            if selected.get("negative_specificity") is not None
            else None
        ),
        "predicted_positive_rate_percent": (
            round(selected["predicted_positive_rate"] * 100, 2)
            if selected.get("predicted_positive_rate") is not None
            else None
        ),
        "actual_positive_rate_percent": (
            round(selected["actual_positive_rate"] * 100, 2)
            if selected.get("actual_positive_rate") is not None
            else None
        ),
        "out_of_sample_observations": selected.get("observations"),
    }


def render_model_scorecard(scorecard):
    """Short human-readable diagnostics; no claim of forecasting edge."""
    if scorecard["mae_percent"] is None or scorecard["best_baseline"] is None:
        return "  Scorecard: insufficient comparable out-of-sample metrics."

    improvement = scorecard["mae_improvement_vs_best_baseline_percentage_points"]
    balanced = scorecard["balanced_directional_accuracy_percent"]
    specificity = scorecard["negative_specificity_percent"]
    balanced_label = (
        f"{balanced:.1f}%" if balanced is not None else "unavailable"
    )
    specificity_label = (
        f"{specificity:.1f}%" if specificity is not None else "unavailable"
    )
    return (
        f"  MAE: model {scorecard['mae_percent']:.3f}% vs best baseline "
        f"({scorecard['best_baseline']}) "
        f"{scorecard['best_baseline_mae_percent']:.3f}%; "
        f"improvement {improvement:+.3f} percentage points "
        "(positive means model has lower MAE); "
        f"balanced direction {balanced_label}; "
        f"negative specificity {specificity_label}."
    )


class Command(BaseCommand):
    help = (
        "Evaluate one ML model on stored stocks using expanding-window "
        "out-of-sample validation and three simple baselines; read-only."
    )

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="+", default=None)
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--horizon", type=int, choices=HORIZONS, default=5)
        parser.add_argument(
            "--common-window", action="store_true",
            help="Use shared calendar date bounds for all selected stocks.",
        )
        parser.add_argument("--model", choices=tuple(MODEL_FACTORIES),
                            default="random_forest")
        parser.add_argument(
            "--feature-set", choices=("price_volume", "market_aligned"),
            default="price_volume",
            help=(
                "price_volume preserves comparable earlier experiments. "
                "market_aligned uses the same market-relative features as "
                "the live API when the complete local FTSE/S&P cache exists; "
                "no Yahoo downloads or silent feature fallback."
            ),
        )
        parser.add_argument("--min-train", type=int, default=500)
        parser.add_argument("--test-size", type=int, default=100)
        parser.add_argument("--output", type=str,
                            help="Optional destination for a JSON research report.")

    def handle(self, *args, **opts):
        limit = opts["limit"]
        min_train = opts["min_train"]
        test_size = opts["test_size"]
        horizon = opts["horizon"]
        if not 1 <= limit <= 100 or min_train < 300 or test_size < 30:
            raise CommandError("Require 1<=limit<=100, min-train>=300, test-size>=30.")
        if test_size < horizon + 2:
            raise CommandError(
                "Test fold must contain at least horizon+2 origins."
            )

        symbols = opts["symbols"]
        if symbols:
            tickers = list(dict.fromkeys(s.strip().upper() for s in symbols if s.strip()))
            if not tickers or len(tickers) > 100:
                raise CommandError("Supply between 1 and 100 stock symbols.")
            stocks = list(Stock.objects.filter(symbol__in=tickers, is_active=True)
                          .order_by("symbol"))
            if len(stocks) != len(tickers):
                raise CommandError("One or more selected stocks do not exist or are inactive.")
        else:
            stocks = list(Stock.objects.filter(is_active=True).order_by("symbol")[:limit])

        today = timezone.localdate()
        common_window = None
        if opts["common_window"]:
            bounds = [
                HistoricalPrice.objects.filter(
                    stock=stock, date__lte=today, close_price__gt=0,
                ).aggregate(first=Min("date"), last=Max("date"))
                for stock in stocks
            ]
            try:
                common_window = common_calendar_window(bounds)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(
                f"Common calendar window: {common_window[0]} to {common_window[1]}"
            )

        report = {
            "common_calendar_window": (
                {
                    "start_date": common_window[0].isoformat(),
                    "end_date": common_window[1].isoformat(),
                    "note": "Same calendar bounds; trading sessions may differ.",
                } if common_window else None
            ),
            "protocol": "Expanding window, no shuffling, H+1-row train/test purge",
            "source": "stored MarketPulse database (no external downloads)",
            "as_of": timezone.localdate().isoformat(),
            "model": opts["model"],
            "horizon_trading_days": horizon,
            "min_train": min_train,
            "test_size": test_size,
            "benchmark_features": (
                "Mandatory same-market cached benchmark; no provider downloads or fallback."
                if opts["feature_set"] == "market_aligned"
                else "Not included; price/volume-only features for comparable earlier experiments."
            ),
            "feature_set": opts["feature_set"],
            "benchmark_data_mode": (
                "local_cache_only" if opts["feature_set"] == "market_aligned"
                else "not_used"
            ),
            "stocks": [],
        }

        wins, evaluated = 0, 0
        for stock in stocks:
            rows = list(
                HistoricalPrice.objects.filter(
                    stock=stock,
                    date__lte=(common_window[1] if common_window else today),
                    **({"date__gte": common_window[0]} if common_window else {}),
                ).order_by("date").values(
                    "date", "open_price", "high_price", "low_price",
                    "close_price", "volume", "is_ohlc_valid", "is_volume_valid",
                )
            )
            item = {"symbol": stock.symbol, "price_observations": len(rows)}

            try:
                if len(rows) < min_train + test_size + horizon + 2:
                    raise ValueError("Insufficient stored price history")
                price_df = pd.DataFrame(rows)
                benchmark_series = None
                if opts["feature_set"] == "market_aligned":
                    benchmark_series = load_cached_benchmark_prices(
                        price_df, stock.exchange
                    )

                X, y = prepare_training_dataset(
                    price_df, benchmark_prices=benchmark_series,
                    horizon=horizon,
                )
                if opts["feature_set"] == "market_aligned":
                    # A silent benchmark-feature omission would make results
                    # incomparable to the market-aware live API. Fail closed.
                    expected = {
                        "benchmark_return_1d", "benchmark_return_20d",
                        "relative_return_1d", "relative_return_5d",
                        "relative_return_20d", "relative_return_60d",
                    }
                    if not expected.issubset(X.columns):
                        raise ValueError(
                            "Incomplete cached benchmark feature coverage."
                        )
                    item["benchmark_ticker"] = benchmark_series.attrs.get("ticker")
                    item["feature_count"] = len(X.columns)
                folds = generate_walk_forward_splits(
                    X, y, minimum_train_size=min_train, test_size=test_size,
                    horizon=horizon, step_size=test_size,
                )
                if len(folds) < 2:
                    raise ValueError("Fewer than two valid walk-forward test folds")
                preds = generate_walk_forward_predictions(
                    X, y, folds, MODEL_FACTORIES[opts["model"]],
                )
                described_folds = [
                    describe_fold(X, fold) for fold in folds
                ]
                details = build_final_validation_report(
                    X, y, described_folds, preds, opts["model"], horizon,
                )
                beat_all = model_beats_all_baselines(details)
                direction_bias = assess_direction_bias(
                    details["metrics"]["selected_model"]
                )
                scorecard = build_model_scorecard(details)
                evaluated += 1
                wins += int(beat_all)
                item.update({
                    "status": "evaluated",
                    "usable_observations": len(X),
                    "usable_start_date": str(X.index[0].date()),
                    "usable_end_date": str(X.index[-1].date()),
                    "folds": len(folds),
                    "fold_metrics": details["fold_metrics"],
                    "out_of_sample_observations": (
                        details["protocol"]["out_of_sample_observations"]
                    ),
                    "beats_all_baselines_on_mae": beat_all,
                    "directional_bias": direction_bias,
                    "scorecard": scorecard,
                    "selected_model_metrics": details["metrics"]["selected_model"],
                    "baseline_metrics": {
                        k: details["metrics"][k]
                        for k in ("zero_return", "historical_mean", "momentum")
                    },
                    "fold_stability": details["fold_stability"],
                })
                verdict = "beat all three baselines" if beat_all else "did not beat all baselines"
                self.stdout.write(f"{stock.symbol}: {len(folds)} folds; {verdict}")
                self.stdout.write(render_model_scorecard(scorecard))
                if direction_bias["warning"]:
                    self.stdout.write(f"  CAUTION: {direction_bias['warning']}")

            except (BenchmarkDataUnavailable, ValueError, TypeError, ArithmeticError) as exc:
                item.update({"status": "insufficient_or_invalid_data", "reason": str(exc)})
                self.stderr.write(f"{stock.symbol}: skipped ({exc})")
            report["stocks"].append(item)

        report["summary"] = {
            "evaluated_stocks": evaluated,
            "stocks_beating_all_baselines_on_mae": wins,
            "excluded_stocks": len(report["stocks"]) - evaluated,
            "ready_for_live_trading": False,
            "warning": (
                "This historical diagnostic is not a deployment certification. "
                "Evaluate multiple models/horizons without selecting on the same "
                "test window; check costs, survivorship, and external data rights."
            ),
        }
        self.stdout.write(
            f"RESULT: {wins}/{evaluated} evaluated stocks beat zero-return, "
            "training-mean and momentum on MAE."
        )

        if opts["output"]:
            destination = Path(opts["output"]).expanduser().resolve()
            if destination.exists():
                raise CommandError(
                    f"Refusing to overwrite existing research report: {destination}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            self.stdout.write(f"Research report saved: {destination}")

        if not evaluated:
            raise CommandError("No stock had sufficient usable observations.")
