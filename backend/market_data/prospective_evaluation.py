"""Pure chronology-safe prospective forecast settlement helpers.

Only stored, valid, post-signal OHLC rows can establish the entry and exit.
A forecast is not mature until its horizon-th subsequent trading observation
AFTER the next-session entry exists and the record was issued before entry.
"""
from decimal import Decimal, InvalidOperation


def prospective_outcome(forecast, observations, *, today):
    """Return outcome dict or None. Never estimates missing future prices.

    observations are date-ordered actual stored trading sessions. The next
    observed session after signal is the entry close; exactly horizon later
    is the exit close. Holidays don't count as trading sessions.
    """
    if forecast.scored_at is not None:
        return None
    rows = sorted(observations, key=lambda row: row["date"])
    eligible = [
        row for row in rows
        if row["date"] > forecast.signal_date and row["date"] <= today
    ]
    if len(eligible) <= forecast.horizon or forecast.horizon <= 0:
        return None
    window = eligible[:forecast.horizon + 1]
    if any(not row.get("is_ohlc_valid", False) for row in window):
        # Never silently compress the horizon by dropping an invalid session.
        return None
    entry = window[0]
    exit_row = window[-1]
    if forecast.created_at.date() >= entry["date"]:
        # The record was created after the entry price was already observable;
        # it cannot be used in honest prospective skill measurement.
        return None
    try:
        entry_price = Decimal(str(entry["close_price"]))
        exit_price = Decimal(str(exit_row["close_price"]))
        if entry_price <= 0 or exit_price <= 0:
            return None
        actual = exit_price / entry_price - 1
    except (InvalidOperation, TypeError, ValueError, ZeroDivisionError):
        return None
    return {
        "entry_date": entry["date"],
        "exit_date": exit_row["date"],
        "entry_price": entry_price,
        "exit_price": exit_price,
        "realized_return": actual.quantize(Decimal("0.0000000001")),
    }


def forecast_skill_summary(forecasts):
    """Simple benchmark: predict zero return for same matured outcomes."""
    scored = [f for f in forecasts if f.realized_return is not None]
    if not scored:
        return {
            "evaluated": 0, "mae": None, "zero_return_baseline_mae": None,
            "beats_zero_baseline": None, "direction_accuracy": None,
            "interval_coverage": None,
        }
    errors = [abs(float(f.realized_return-f.predicted_return)) for f in scored]
    baseline = [abs(float(f.realized_return)) for f in scored]
    sign_correct = [
        (f.realized_return > 0 and f.predicted_return > 0)
        or (f.realized_return < 0 and f.predicted_return < 0)
        or (f.realized_return == 0 and f.predicted_return == 0)
        for f in scored
    ]
    covered = [
        f.lower_return <= f.realized_return <= f.upper_return
        for f in scored
        if f.lower_return is not None and f.upper_return is not None
    ]
    mae = sum(errors)/len(errors)
    baseline_mae = sum(baseline)/len(baseline)
    return {
        "evaluated": len(scored),
        "mae": round(mae, 8),
        "zero_return_baseline_mae": round(baseline_mae, 8),
        "beats_zero_baseline": bool(mae < baseline_mae),
        "direction_accuracy": round(sum(sign_correct)/len(scored), 4),
        "interval_coverage": round(sum(covered)/len(covered), 4) if covered else None,
    }
