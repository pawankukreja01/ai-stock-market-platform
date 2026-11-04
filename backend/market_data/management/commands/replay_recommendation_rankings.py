"""No-write, offline recommendation ranking replay on a frozen test cohort."""
import hashlib
import json
import os
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from market_data.recommendation_replay import (
    evaluate_replay_period, summarize_periods, validate_replay_symbols,
)
from stocks.models import Stock


class Command(BaseCommand):
    help = "Read-only, explicitly bounded historical ranking replay in restored test DB."

    def add_arguments(self, parser):
        parser.add_argument("--cohort-file", required=True, help='JSON {"symbols": [...]}')
        parser.add_argument("--start-date", required=True)
        parser.add_argument("--end-date", required=True)
        parser.add_argument("--horizon", type=int, choices=[1, 5, 20, 60], default=20)
        parser.add_argument("--calendar-step", type=int, default=30)
        parser.add_argument("--top-k", type=int, default=5)
        parser.add_argument("--risk", choices=["low", "moderate", "high"], default="moderate")
        parser.add_argument("--horizon-months", type=int, default=12)
        parser.add_argument("--cost-bps-per-side", type=float, default=10.0)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **opts):
        name = "marketpulse_restored_test"
        if os.environ.get("DB_NAME") != name or connection.settings_dict["NAME"] != name:
            raise CommandError("Refusing to replay outside explicit restored research DB.")
        try:
            raw = Path(opts["cohort_file"]).expanduser().read_bytes()
            manifest = json.loads(raw)
            symbols = validate_replay_symbols(manifest["symbols"])
            start = date.fromisoformat(opts["start_date"])
            end = date.fromisoformat(opts["end_date"])
        except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise CommandError(f"Invalid research cohort or dates: {exc}") from exc
        if not (start < end <= date.today()) or (end - start).days > 365 * 3:
            raise CommandError("Require valid past 3-year date range (start before end).")
        if not 1 <= opts["top_k"] < len(symbols) or opts["top_k"] > 20:
            raise CommandError("top-k must be 1–20 and smaller than the cohort.")
        if not 1 <= opts["horizon_months"] <= 600:
            raise CommandError("Invalid investment horizon.")
        if not 7 <= opts["calendar_step"] <= 365:
            raise CommandError("Calendar step must be 7–365 days.")
        cost = opts["cost_bps_per_side"]
        if not 0 <= cost <= 100 or not __import__("math").isfinite(cost):
            raise CommandError("Cost per side must be finite and in 0–100 bps.")
        destination = Path(opts["output"]).expanduser().resolve()
        if destination.exists():
            raise CommandError("Refusing to overwrite an earlier research report.")
        present = set(
            Stock.objects.filter(symbol__in=symbols, is_active=True)
            .values_list("symbol", flat=True)
        )
        if present != set(symbols):
            raise CommandError("Frozen cohort contains unknown or inactive stocks.")
        signal_dates = []
        current = start
        while current <= end:
            signal_dates.append(current)
            current += timedelta(days=opts["calendar_step"])
        if len(signal_dates) > 160:
            raise CommandError("Too many signal dates.")

        periods = []
        for when in signal_dates:
            period = evaluate_replay_period(
                signal_date=when,
                symbols=symbols,
                risk_tolerance=opts["risk"],
                horizon_months=opts["horizon_months"],
                horizon=opts["horizon"],
                top_k=opts["top_k"],
                round_trip_bps=cost,
            )
            periods.append(period)
            self.stdout.write(f'{when.isoformat()}: {period["status"]}')
        report = {
            "status": "research_only_no_trading_approval",
            "database": name, "read_only": True, "provider_requests": 0,
            "source_cohort_sha256": hashlib.sha256(raw).hexdigest(),
            "symbols": symbols,
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "top_k": opts["top_k"], "horizon_trading_sessions": opts["horizon"],
            "calendar_step_days": opts["calendar_step"],
            "cost_bps_per_side": cost,
            "outcome_target": "next-observed-close to H-session-exit close, unadjusted",
            "ranking_policy": "existing provisional fundamental/momentum/risk/sentiment score",
            "baseline": "equal-weight of same ranked-eligible universe; same assumed round-trip fees",
            "known_limitations": [
                "Current stock list and active flags cause survivorship bias.",
                "Original filing/publication availability may be unknown; late-ingested "
                "backfills are excluded, but this is not a verified point-in-time feed.",
                "Common rebalance calendar is approximate, does not model exchange holidays, "
                "time zones, order execution or volume/liquidity.",
                "Stock returns omit dividends, FX, spreads and slippage and are not returns "
                "of an executable portfolio.",
                "This previously inspected historical data is not an untouched holdout. "
                "A future prospective period is needed before any performance claims.",
            ],
            "periods": periods,
            "summary": summarize_periods(periods),
            "approved_for_live_predictions": False,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2, allow_nan=False)
            output.write("\n")
        self.stdout.write(self.style.SUCCESS(f"Saved research report: {destination}"))
