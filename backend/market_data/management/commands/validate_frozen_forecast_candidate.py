"""Offline frozen candidate evaluation; explicit test DB only, no writes to DB."""
import json
import os
from pathlib import Path
from statistics import median

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Max, Min
from django.utils import timezone
from django.utils.dateparse import parse_date

from market_data.frozen_research_candidate import (
    FROZEN_SPEC, evaluate_frozen_candidate, load_frozen_spec,
)
from market_data.management.commands.experiment_forecast_pipeline import load_locked_cohort
from market_data.management.commands.validate_stock_forecasts import common_calendar_window
from market_data.models import HistoricalPrice
from ml_engine import prepare_training_dataset
from stocks.models import Stock

RESEARCH_DB = "marketpulse_restored_test"


def summarize_horizon(rows, horizon):
    valid = [
        row["horizons"][str(horizon)]
        for row in rows
        if row["horizons"][str(horizon)]["status"] == "evaluated"
    ]
    deltas = [
        item["scorecard"]["mae_improvement_vs_best_baseline_percentage_points"]
        for item in valid
        if item["scorecard"]["mae_improvement_vs_best_baseline_percentage_points"] is not None
    ]
    return {
        "horizon": horizon,
        "stocks_evaluated": len(valid),
        "stocks_excluded": len(rows) - len(valid),
        "stocks_beating_all_three_baselines": sum(
            item["beats_all_baselines_on_mae"] for item in valid
        ),
        "median_improvement_over_best_baseline_pp": (
            round(median(deltas), 4) if deltas else None
        ),
        "deployment_approved": False,
    }


class Command(BaseCommand):
    help = "Read-only frozen Ridge alpha=1000 evaluation on exactly 33 verified research stocks."

    def add_arguments(self, parser):
        parser.add_argument("--cohort-file", required=True,
                            help='Recovered original 33 ticker JSON: {"symbols": [...]}')
        parser.add_argument("--as-of", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        if (
            os.environ.get("DB_NAME") != RESEARCH_DB
            or connection.settings_dict.get("NAME") != RESEARCH_DB
        ):
            raise CommandError(
                "Refusing frozen research outside explicit DB_NAME=marketpulse_restored_test."
            )
        try:
            config, config_hash = load_frozen_spec()
            symbols, cohort_hash = load_locked_cohort(options["cohort_file"])
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise CommandError(str(exc)) from exc
        as_of = parse_date(options["as_of"])
        if as_of is None or as_of > timezone.localdate():
            raise CommandError("--as-of requires YYYY-MM-DD not in the future.")
        destination = Path(options["output"]).expanduser().resolve()
        if destination.exists():
            raise CommandError("Refusing to overwrite an existing frozen-candidate report.")
        stocks = list(
            Stock.objects.filter(symbol__in=symbols, is_active=True).order_by("symbol")
        )
        if len(stocks) != len(symbols):
            raise CommandError("Frozen 33-stock cohort contains missing/inactive tickers.")
        bounds = [
            HistoricalPrice.objects.filter(
                stock=stock, date__lte=as_of, close_price__gt=0,
            ).aggregate(first=Min("date"), last=Max("date"))
            for stock in stocks
        ]
        try:
            first, last = common_calendar_window(bounds)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        result = {
            "candidate": config,
            "candidate_lock_sha256": config_hash,
            "cohort_manifest_sha256": cohort_hash,
            "cohort_symbols": symbols,
            "database": RESEARCH_DB,
            "cutoff": as_of.isoformat(),
            "common_calendar_window": {"first": first.isoformat(), "last": last.isoformat()},
            "source": "local restored test database only; no market provider access",
            "read_only_database": True,
            "historical_window_role": "development_diagnostic_not_independent_holdout",
            "approved_for_live_prediction": False,
            "future_performance_established": False,
            "note": (
                "Candidate was selected after inspection of historical development folds. "
                "This study cannot establish independent prospective predictive skill."
            ),
            "stocks": [],
        }
        for stock in stocks:
            rows = list(
                HistoricalPrice.objects.filter(
                    stock=stock, date__gte=first, date__lte=last,
                ).order_by("date").values(
                    "date", "open_price", "high_price", "low_price",
                    "close_price", "volume", "is_ohlc_valid", "is_volume_valid",
                )
            )
            item = {"symbol": stock.symbol, "price_rows": len(rows), "horizons": {}}
            for horizon in FROZEN_SPEC["horizons_trading_days"]:
                try:
                    if len(rows) < config["min_train"] + config["test_size"] + horizon + 2:
                        raise ValueError("Not enough stored OHLCV rows for this horizon.")
                    X, y = prepare_training_dataset(pd.DataFrame(rows), horizon=horizon)
                    if len(X) < config["min_train"] + config["test_size"] + horizon + 2:
                        raise ValueError("Not enough valid feature/target rows for this horizon.")
                    item["horizons"][str(horizon)] = evaluate_frozen_candidate(
                        X, y, horizon=horizon
                    )
                    self.stdout.write(f"{stock.symbol} {horizon}d: evaluated")
                except (ValueError, TypeError, ArithmeticError) as exc:
                    item["horizons"][str(horizon)] = {
                        "status": "insufficient_or_invalid_data",
                        "reason": str(exc),
                    }
                    self.stderr.write(f"{stock.symbol} {horizon}d: excluded ({exc})")
            result["stocks"].append(item)
        result["summary"] = {
            "by_horizon": [
                summarize_horizon(result["stocks"], h)
                for h in FROZEN_SPEC["horizons_trading_days"]
            ],
            "model_promotion_approved": False,
        }
        if not any(h["stocks_evaluated"] for h in result["summary"]["by_horizon"]):
            raise CommandError("No stock/horizon has enough valid OOS folds; no report written.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as output:
            json.dump(result, output, allow_nan=False, indent=2)
            output.write("\n")
        self.stdout.write(f"Frozen candidate research saved: {destination}")
