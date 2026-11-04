# MarketPulse — forecast model evidence (2026-11-04)

**Status: experimental; no proven baseline-relative outperformance across the tested stocks.**

## Evaluation sources and comparability

- Actual runs supplied from the local `marketpulse_restored_test` database on 2026-11-04, with research cutoff `2026-11-02`: `random_forest` and `zero_anchor_ridge` on AAPL, MSFT, NVDA and ABF.L.
- Previously saved `marketpulse_xgboost_5d_validation.json`, `marketpulse_rf_5d_validation.json` and `marketpulse_linear_5d_validation.json` use cutoff `2026-11-03`, with AAPL, MSFT and NVDA only.
- The archived Random Forest and baseline MAEs match the supplied current run to three decimals for those three stocks. This is strong consistency evidence but **not** a claim that XGBoost was re-run on 2026-11-04 or that every underlying raw row is identical.
- The parameters are 5 trading days, 500 minimum train samples, 100 test samples per fold, and expanding-window chronological validation with an H+1-row purge. The archived reports are price/volume-only, not a final holdout.
- The research dataset contains 184 stocks and 233,219 historical-price rows in a **local** restored test database. The independent Docker preview DB contains 0 historical prices and 0 prospective forecasts.

## Mean absolute forecast return error (percent; lower is better)

| Stock | Best simple baseline | Random Forest | Zero-anchor Ridge | XGBoost (archived) |
|---|---:|---:|---:|---:|
| AAPL | 3.119 | 3.227 | 3.263 | 3.606 |
| ABF.L | 2.536 | 2.885 | 2.716 | unavailable |
| MSFT | 2.987 | 3.132 | 3.058 | 3.389 |
| NVDA | 4.449 | 4.844 | **4.418** | 5.404 |

- Random Forest: 0/4 stocks beat zero-return, historical-mean and momentum baselines.
- Zero-anchor Ridge: 1/4 stocks beat all three; NVDA improvement over the *best* baseline is only **0.031 percentage points**.
- Archived XGBoost: 0/3 stocks beat all three baselines.
- Conservative Random Forest: **not measured** on the exact local dataset; no results should be invented.
- The default Random Forest on NVDA predicted an increase 99.0% of the time, versus 55.8% actually positive, with 0.9% negative specificity.
- Ridge improved NVDA negative specificity to 27.1%, but predicted positive returns 77.4% of the time.
- AAPL, ABF.L and MSFT Ridge balanced directional accuracy stayed approximately 50%; NVDA reached 54.1%.

## Decision

**Do not promote or replace the live model based on this development sample.** Keep predictions labelled experimental, show error and uncertainty against baselines, and avoid claiming a definitive price accuracy or profitability statistic.

## Remaining verification gates

1. Run conservative forest for all four stocks and XGBoost for ABF.L against the frozen 2026-11-02 local dataset.
2. Recover/version the exact 33-stock cohort and price/return basis; do not substitute the full catalogue silently.
3. Run identical stock/horizon/feature/fold comparisons for 1, 5, 20, 60 trading days with data-quality exclusions and no lookahead.
4. Reserve an untouched validation period; report corrected uncertainty and trial-selection limitations.
5. Track *real* future forecast issues and observed outcomes; the restored test DB's prospective table migration is still pending and must not be applied before a separate backup/review.
6. Audit trading execution assumptions, transaction costs, dividends and corporate actions before any real-money suitability claim.

**Safety:** Never run ingestion/migrations/writes against the original `ai_stock_market` database. Current research validation commands are read-only on `marketpulse_restored_test`.

Related: #5, PR #4.