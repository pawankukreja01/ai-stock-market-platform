# Prospective forecast verification — no lookahead

## Purpose

Historical backtests alone cannot prove a predictive advantage. This
feature records a **server-computed forecast before its next-session
entry** and compares it with real future closes only after the full
requested trading-session horizon is observed.

The `ProspectiveForecast` table stores the symbol, model, horizon,
signal date, predicted return, optional calibration interval, confidence,
and creation time separately from the later observed entry/exit prices
and realized return. There is a unique issuance row per
`(stock, model, horizon, signal_date)`: repeated issuance does not
overwrite the first prediction or rewrite the observed outcome.

## Critical forecast target

The existing ML endpoint defines:

```
return = close_price[t + horizon + 1] / close_price[t + 1] - 1
```

The **entry** is the next actual session's close after the signal; the
**exit** is the close exactly `horizon` observed sessions after entry.
The earlier signal-day closing price is not substituted for the entry.
Unadjusted prices exclude dividends; commissions, spread, slippage,
corporate actions and taxes are not represented.

An observation must be dated no later than today. A forecast is only
scored if the issue timestamp strictly precedes the entry date.
Invalid OHLC observations within the settlement window block settlement
rather than silently compressing the trading horizon.

Caution: stored data may have missing entire sessions; holiday-aware
gap detection and a separate licensed market calendar are needed for
institutional-grade settlement. Existing source quality is not guaranteed.

## Issue new forecasts (opt-in and staff-only)

Authenticated staff can call:

`POST /api/prospective-forecasts/capture/`

with JSON containing `symbol`, `model` (linear_regression,
random_forest, xgboost), and `horizon` (1, 5, 20, 60, 126, 252).
The server independently calculates its forecast; it never accepts a
client-submitted return. Standard session and CSRF protections apply.

**A write is permitted only when both the environment variable and
configured Django database name equal `marketpulse_restored_test`.**
Stale signal dates (older than seven calendar days) and future dates
are rejected. This prevents generating fake prospective history from
old saved data. The endpoint is not a scheduler and cannot start
unattended model training.

Capturing a prediction requires sufficient historical data and may
be resource intensive; use only after authorization and normal
provider access is restored.

## View results (read-only)

Authenticated users can open `/forecast-performance` or read
`GET /api/prospective-forecasts/results/` (optional `?symbol=AAPL`).
A maximum of 1,000 recent recorded observations is summarized.

Metrics are issued count, pending count, evaluated count,
model MAE, zero-return baseline MAE, directional accuracy and,
where calibration intervals exist, interval coverage. With zero
realized outcomes the skill fields are `null`, not 0% or 100%.

## Settle future outcomes

Default settlement is a **read-only preview**:

```bash
cd ~/Desktop/ai-stock-market-platform/backend
DB_NAME=marketpulse_restored_test python manage.py evaluate_prospective_forecasts
```

Only after inspecting the preview, using the restored test database,
and confirming that real future observations exist, apply outcomes:

```bash
DB_NAME=marketpulse_restored_test python manage.py evaluate_prospective_forecasts --execute
```

The command does not contact Yahoo. It only fills pending outcome fields;
it cannot update a recorded model prediction, and it is guarded against
the original `ai_stock_market` database.

## What cannot be marked complete now

Real future exits cannot be generated retrospectively. Reliable skill
requires an independently collected prospective sample, multiple
market regimes, representative stocks, a suitable unchanging evaluation
protocol, transaction costs and bias checks. This release candidate
delivers *measurement infrastructure*, not proven profitability.
