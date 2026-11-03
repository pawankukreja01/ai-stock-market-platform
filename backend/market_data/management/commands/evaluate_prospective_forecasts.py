"""Explicit, controlled settlement of previously issued forecasts.

Default: read-only preview. --execute writes *only* completed outcome fields
to the explicitly designated restored test database. No Yahoo calls.
"""
import os
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from market_data.models import HistoricalPrice, ProspectiveForecast
from market_data.prospective_evaluation import prospective_outcome


class Command(BaseCommand):
    help = "Preview mature prospective forecasts, optionally settle in restored test DB."

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true", help="Settle mature forecasts into restored test DB.")
        parser.add_argument("--symbol", default="", help="Optional single symbol.")
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args, **options):
        if (
            os.environ.get("DB_NAME") != "marketpulse_restored_test"
            or connection.settings_dict["NAME"] != "marketpulse_restored_test"
        ):
            raise CommandError("Requires explicit DB_NAME=marketpulse_restored_test.")
        limit = options["limit"]
        if limit < 1 or limit > 2000:
            raise CommandError("--limit must be between 1 and 2000.")
        forecasts = ProspectiveForecast.objects.filter(scored_at__isnull=True).select_related("stock")
        symbol = options["symbol"].strip().upper()
        if symbol:
            forecasts = forecasts.filter(stock__symbol=symbol)
        forecasts = list(forecasts.order_by("created_at")[:limit])
        by_stock = defaultdict(list)
        for forecast in forecasts:
            by_stock[forecast.stock_id].append(forecast)

        today = timezone.localdate()
        eligible = 0
        pending = 0
        for stock_id, rows in by_stock.items():
            earliest = min(row.signal_date for row in rows)
            prices = list(
                HistoricalPrice.objects.filter(
                    stock_id=stock_id, date__gte=earliest, date__lte=today
                ).order_by("date").values("date", "close_price", "is_ohlc_valid")
            )
            for forecast in rows:
                outcome = prospective_outcome(forecast, prices, today=today)
                if outcome is None:
                    pending += 1
                    continue
                eligible += 1
                self.stdout.write(
                    f"{forecast.stock.symbol} {forecast.model_key} "
                    f"{forecast.horizon}D from {forecast.signal_date}: "
                    f"entry {outcome['entry_date']}, exit {outcome['exit_date']}, "
                    f"actual return {outcome['realized_return']}"
                )
                if options["execute"]:
                    # A single guarded update per pending row: no target or
                    # issuance field can ever be overwritten by settlement.
                    with transaction.atomic():
                        ProspectiveForecast.objects.filter(
                            pk=forecast.pk, scored_at__isnull=True
                        ).update(**outcome, scored_at=timezone.now())

        self.stdout.write(
            f"Evaluated {len(forecasts)} queued: {eligible} mature, "
            f"{pending} pending. "
            + ("Saved mature outcomes." if options["execute"]
               else "PREVIEW ONLY: zero database writes.")
        )
