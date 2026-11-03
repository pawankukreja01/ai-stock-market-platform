"""Read-only audit of OHLC and adjusted-close provenance for ML research.

These flags are *investigation candidates*. A large legitimate price move or
provider adjustment is not automatically corrupt data; no rows are rewritten.
"""

from datetime import date
import math

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from market_data.models import HistoricalPrice
from stocks.models import Stock


def _positive_finite(value):
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def audit_price_rows(rows, *, today, jump_threshold=0.35, factor_threshold=0.10):
    """Review successive stored daily observations without inventing prices.

    Close is not automatically equivalent to adjusted close. Ingested Yahoo
    close prices may already be split-adjusted; adjustment-factor shifts and
    extreme jumps are clues for an analyst, not definitive corporate actions.
    """
    if not 0 < jump_threshold < 1 or not 0 < factor_threshold < 1:
        raise ValueError("thresholds must lie strictly between zero and one")

    result = {
        "observations": 0,
        "ohlc_invalid": 0,
        "volume_invalid": 0,
        "missing_or_invalid_adjusted_close": 0,
        "future_dated_rows": 0,
        "large_close_moves": [],
        "large_adjustment_factor_changes": [],
        "large_close_move_count": 0,
        "large_adjustment_factor_change_count": 0,
    }
    previous_date = None
    previous_close = None
    previous_factor = None

    for row in rows:
        when = row["date"]
        result["observations"] += 1
        if previous_date is not None and when <= previous_date:
            raise ValueError("Price rows must be strictly date-ordered")
        previous_date = when

        if when > today:
            result["future_dated_rows"] += 1

        ohlc_valid = row.get("is_ohlc_valid") is True
        if not ohlc_valid:
            result["ohlc_invalid"] += 1
        if row.get("is_volume_valid") is not True:
            result["volume_invalid"] += 1

        close = _positive_finite(row.get("close_price"))
        adjusted = _positive_finite(row.get("adjusted_close"))
        if adjusted is None:
            result["missing_or_invalid_adjusted_close"] += 1

        # Don't calculate returns across missing or explicitly invalid candles.
        if not ohlc_valid or close is None or adjusted is None:
            previous_close = None
            previous_factor = None
            continue

        factor = adjusted / close
        if previous_close is not None:
            change = close / previous_close - 1.0
            if abs(change) >= jump_threshold:
                result["large_close_move_count"] += 1
                if len(result["large_close_moves"]) < 5:
                    result["large_close_moves"].append({
                        "date": when.isoformat(),
                        "close_return_percent": round(100 * change, 2),
                    })
        if previous_factor is not None:
            factor_change = factor / previous_factor - 1.0
            if abs(factor_change) >= factor_threshold:
                result["large_adjustment_factor_change_count"] += 1
                if len(result["large_adjustment_factor_changes"]) < 5:
                    result["large_adjustment_factor_changes"].append({
                        "date": when.isoformat(),
                        "relative_factor_change_percent": round(
                            100 * factor_change, 2
                        ),
                    })

        previous_close = close
        previous_factor = factor

    return result


class Command(BaseCommand):
    help = (
        "Read-only check of stock price gaps, suspicious close jumps, "
        "and adjusted-close factor changes before forecast retraining."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols", nargs="+", required=True,
            help="One or more active tickers, e.g. AAPL MSFT NVDA.",
        )

    def handle(self, *args, **options):
        symbols = list(dict.fromkeys(
            symbol.strip().upper()
            for symbol in options["symbols"]
            if symbol.strip()
        ))
        if not symbols or len(symbols) > 25:
            raise CommandError("Supply between 1 and 25 stock symbols.")

        stocks = list(
            Stock.objects.filter(is_active=True, symbol__in=symbols)
            .order_by("symbol")
        )
        if len(stocks) != len(symbols):
            raise CommandError("Unknown or inactive stock symbol in request.")

        today = timezone.localdate()
        self.stdout.write(f"Read-only prediction price audit: {today}")
        self.stdout.write(
            "Price jumps and factor changes are review flags, "
            "not confirmed splits, errors or trading signals."
        )

        for stock in stocks:
            rows = HistoricalPrice.objects.filter(
                stock=stock
            ).order_by("date").values(
                "date", "close_price", "adjusted_close",
                "is_ohlc_valid", "is_volume_valid",
            )
            result = audit_price_rows(rows, today=today)
            self.stdout.write(
                f"{stock.symbol}: {result['observations']} observations; "
                f"invalid OHLC={result['ohlc_invalid']}; "
                f"invalid volume={result['volume_invalid']}; "
                f"missing adjusted={result['missing_or_invalid_adjusted_close']}; "
                f"future dates={result['future_dated_rows']}; "
                f"large close moves={result['large_close_move_count']}; "
                f"large adjustment changes={result['large_adjustment_factor_change_count']}"
            )
            for entry in result["large_close_moves"]:
                self.stdout.write(
                    f"  Close jump {entry['date']}: "
                    f"{entry['close_return_percent']:+.2f}%"
                )
            for entry in result["large_adjustment_factor_changes"]:
                self.stdout.write(
                    f"  Adjustment factor shift {entry['date']}: "
                    f"{entry['relative_factor_change_percent']:+.2f}%"
                )
