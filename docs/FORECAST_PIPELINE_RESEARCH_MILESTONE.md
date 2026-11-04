# Forecast Pipeline Research — next milestone (experimental)

## Scope and status

- Implements **research-only** fixed-grid comparisons for expanding-vs-rolling training windows (500 / 750 historical observations), stronger Ridge regularization (`alpha=100,300,1000`), and new trailing-volatility-normalized return features.
- Uses identical chronological out-of-sample fold dates with an H+1-row label purge. Feature construction and model imputation/scaling use only the training block and observations available by the forecast origin.
- Optional same-market features are loaded only from the **existing local cache**; missing benchmark data fails closed, with no silent substitutions.
- The live ML API stays unchanged. **No new accuracy result has been measured for these candidates yet.**
- The `/forecast-reliability` workspace page displays a **versioned historical snapshot** from four verified 5-day model reports on AAPL, ABF.L, MSFT and NVDA. It is not a live accuracy feed; no prospective samples or independently verified interval calibration were available. It reports uncertainty as **Not measured**, never 0%.
- The companion endpoint `GET /api/forecast-reliability/` is authenticated, reads a static JSON research artifact, issues no provider or database calls, and marks responses `Cache-Control: private, no-store`.

## Reproduce the next experiment

From the developer's **Mac** and existing `backend/` directory, with your existing virtualenv and the restored test database accessible:

```bash
DB_NAME=marketpulse_restored_test python manage.py experiment_forecast_pipeline \
  --symbols AAPL MSFT NVDA ABF.L \
  --horizon 5 --as-of 2026-11-02 \
  --min-train 500 --test-size 100 \
  --windows expanding 500 750 \
  --alphas 100 300 1000 \
  --output ../marketpulse_model_evaluation/pipeline_ablation_5d_20261102.json
```

Research output is a new JSON file and **cannot overwrite** an existing report. The command checks the environment variable and Django connection both identify `marketpulse_restored_test`; it refuses the original `ai_stock_market` DB. No historical-data writes, provider downloads, migrations, or trading operations.

The default experiment evaluates two feature sets (price/volume only and price/volume plus trailing-volatility-normalized features). Run an optional **separate** experiment with `--include-market` when a complete local same-market benchmark is available, and save to a different output filename. The paired market study uses dates shared by both feature sets and does not silently omit missing index features.

### The planned 33-stock cohort

The exact 33-symbol source manifest from prior research has not yet been recovered. **Do not guess, invent or replace it with the current 184-stock universe.** Once recovered, create a frozen JSON manifest of:

```json
{"symbols": ["<33 exact previously selected ticker symbols>"]}
```

The example above is a *template*, not a usable manifest. The runner requires exactly 33 normalized unique symbols for `--cohort-file`, records its SHA-256, and validates all stocks against the database catalogue. Evaluate four horizons `1,5,20,60` in separate files with a fixed cohort, settings and independent dates.

Before claiming any performance improvement, reserve a genuinely untouched chronological period, avoid adaptive model selection on already inspected folds, audit OHLC/corporate-action treatment, evaluate non-overlapping horizon decisions and realistic transaction costs, and record real future predictions.

## Tests and review

- New backend tests cover original-database refusal, matched folds, window purge, zero return unchanged by volatility features, fixed regularization, valid historical research provenance and authenticated read-only endpoint.
- Frontend tests cover missing uncertainties, signed baseline comparisons and readable model labels.
- The existing Django/Node/Playwright CI is extended to integration-branch PRs; the developer must review its results before merging.
- **Do not merge this research branch or switch the live predictor on the basis of a better development-fold score.**

Existing project PR #4 remains separate. The original `ai_stock_market` database and Docker preview volume are intentionally untouched.
