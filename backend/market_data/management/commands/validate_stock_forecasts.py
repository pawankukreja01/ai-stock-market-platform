"""Read-only, reproducible multi-stock walk-forward research diagnostic.

This evaluates stored history, never places trades, never alters the database,
and intentionally does NOT declare a selected model investment-ready.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from stocks.models import Stock
from market_data.models import HistoricalPrice
from ml_engine import prepare_training_dataset
from ml_models import (
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
)
from walk_forward import generate_walk_forward_splits
from backtesting import generate_walk_forward_predictions
from ml_final_validation import build_final_validation_report


MODEL_FACTORIES = {
    "linear_regression": create_linear_regression_model,
    "random_forest": create_random_forest_model,
    "xgboost": create_xgboost_model,
}
HORIZONS = (1, 5, 20, 60, 126, 252)


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


class Command(BaseCommand):
    help = (
        "Evaluate one ML model on stored stocks using expanding-window "
        "out-of-sample validation and three simple baselines; read-only."
    )

    def add_arguments(self, parser):
        parser.add_argument("--symbols", nargs="+", default=None)
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--horizon", type=int, choices=HORIZONS, default=5)
        parser.add_argument("--model", choices=tuple(MODEL_FACTORIES),
                            default="random_forest")
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

        report = {
            "protocol": "Expanding window, no shuffling, H+1-row train/test purge",
            "source": "stored MarketPulse database (no external downloads)",
            "as_of": timezone.localdate().isoformat(),
            "model": opts["model"],
            "horizon_trading_days": horizon,
            "min_train": min_train,
            "test_size": test_size,
            "benchmark_features": (
                "Not included; this standalone diagnostic compares "
                "price/volume-only features across assets."
            ),
            "stocks": [],
        }

        wins, evaluated = 0, 0
        for stock in stocks:
            rows = list(
                HistoricalPrice.objects.filter(
                    stock=stock, date__lte=timezone.localdate()
                ).order_by("date").values(
                    "date", "open_price", "high_price", "low_price",
                    "close_price", "volume", "is_ohlc_valid", "is_volume_valid",
                )
            )
            item = {"symbol": stock.symbol, "price_observations": len(rows)}

            try:
                if len(rows) < min_train + test_size + horizon + 2:
                    raise ValueError("Insufficient stored price history")
                X, y = prepare_training_dataset(
                    pd.DataFrame(rows), horizon=horizon,
                )
                folds = generate_walk_forward_splits(
                    X, y, minimum_train_size=min_train, test_size=test_size,
                    horizon=horizon, step_size=test_size,
                )
                if len(folds) < 2:
                    raise ValueError("Fewer than two valid walk-forward test folds")
                preds = generate_walk_forward_predictions(
                    X, y, folds, MODEL_FACTORIES[opts["model"]],
                )
                details = build_final_validation_report(
                    X, y, folds, preds, opts["model"], horizon,
                )
                beat_all = model_beats_all_baselines(details)
                evaluated += 1
                wins += int(beat_all)
                item.update({
                    "status": "evaluated",
                    "usable_observations": len(X),
                    "folds": len(folds),
                    "out_of_sample_observations": (
                        details["protocol"]["out_of_sample_observations"]
                    ),
                    "beats_all_baselines_on_mae": beat_all,
                    "selected_model_metrics": details["metrics"]["selected_model"],
                    "baseline_metrics": {
                        k: details["metrics"][k]
                        for k in ("zero_return", "historical_mean", "momentum")
                    },
                    "fold_stability": details["fold_stability"],
                })
                verdict = "beat all three baselines" if beat_all else "did not beat all baselines"
                self.stdout.write(f"{stock.symbol}: {len(folds)} folds; {verdict}")

            except (ValueError, TypeError, ArithmeticError) as exc:
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
