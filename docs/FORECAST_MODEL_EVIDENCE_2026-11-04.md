# MarketPulse forecast model evidence — updated 2026-11-04

**Research result: no consistent baseline-relative forecasting advantage, and no model is approved for trading or for promotion to the live predictor.**

## Sources and integrity

Four freshly executed reports were supplied from the local `marketpulse_restored_test` data set:

| File | SHA-256 |
|---|---|
| `random_forest.json` | `45cda3340a930a86b5c07214a5fe3633950cd5e59c467ce07f08f31a92d71a6a` |
| `conservative_forest.json` | `99eb83dad28ce5eca751cf07b78fd0b42f93e708a80917c9eedea8823f433b23` |
| `zero_anchor_ridge.json` | `bcc281045183f68c3db605d256ce9aec7e15b6fc21d655c7b55980358748f920` |
| `xgboost.json` | `683fbe75d35c56257fb1a3e2b5323353cc3107fea44df6d7cd25a7ca6938ae2c` |

**Identical across all reports:** 2026-11-02 `--as-of`, 5-session target, `--min-train 500`, `--test-size 100`, `price_volume` features, expanding-window folds, H+1 train/test purge. Per-stock fold date ranges, number of held-out observations, and every baseline metric are identical across the four reports. AAPL: 17 folds/1,700 held-out predictions. ABF.L, MSFT, NVDA: each five folds/500 held-out predictions.

These are historical *development diagnostics*, not an untouched final holdout. There is no prospective outcome sample in these reports. The raw daily-price dataset remains on the developer's Mac and was **not** included in the submitted JSON summaries.

## Five-day mean absolute return forecast error (MAE; percent/percentage points)

**Lower is better**; predicted return error is not the same as percentage accuracy of stock price.

| Stock | Best simple baseline | Regular RF | Conservative RF | Zero-anchor Ridge | XGBoost |
|---|---:|---:|---:|---:|---:|
| AAPL | **3.119%** (historical mean) | 3.227% | 3.147% | 3.263% | 3.606% |
| ABF.L | **2.536%** (zero return) | 2.885% | 2.725% | 2.716% | 3.251% |
| MSFT | **2.987%** (zero return) | 3.132% | 3.047% | 3.058% | 3.389% |
| NVDA | 4.449% (zero return) | 4.844% | 4.602% | **4.418%** | 5.404% |

Counts beating *all three* matched baselines (zero return, training historical mean, momentum): **regular RF 0/4; conservative RF 0/4; Ridge 1/4; XGBoost 0/4.** Only Ridge on NVDA is better than the strongest baseline: +0.031 percentage points of average absolute return error. That small historical improvement should not be promoted to an independent statistical/financial edge.

The strongest **ML** for AAPL/MSFT by MAE is conservative RF, and for ABF.L/NVDA is zero-anchor Ridge. Choosing between them *using these same test outcomes* is not a legitimate out-of-sample model-selection policy.

## Directional behavior

| Model | NVDA balanced direction | NVDA negative specificity | NVDA predicted positive | NVDA actually positive |
|---|---:|---:|---:|---:|
| Regular RF | 49.9% | 0.9% | 99.0% | 55.8% |
| Conservative RF | 50.0% | **0.0%** | **100.0%** | 55.8% |
| Zero-anchor Ridge | 54.1% | 27.1% | 77.4% | 55.8% |
| XGBoost | 55.1% | 28.5% | 77.2% | 55.8% |

Conservative RF improves magnitude error versus regular RF but makes the upside-bias problem *worse* for NVDA (every test return is predicted positive). XGBoost obtains the highest NVDA balanced directional accuracy of these four yet has the worst MAE. This demonstrates that direction and return-magnitude performance must be evaluated separately.

For AAPL, the Ridge positive-return prediction rate is only 36.2% versus 57.4% actual positive returns, illustrating a possible overcorrection.

## Development decision

- **Do not change live model defaults or advertise profitable predictions.** Maintain experimental labels, baseline-relative MAE, balanced directional metrics, sample counts, freshness and interval calibration on the research UX.
- Run an **immutable 33-stock / four-horizon** study (1, 5, 20, 60 sessions) after recovering the actual 33-stock cohort manifest; do not silently substitute the full 184-stock catalogue.
- Investigate research-only shrinkage, rolling vs expanding train windows, market-relative features, regime and volatility-aware inputs, and leakage-safe nested selection. These are experimental hypotheses, not measured improvements.
- Audit price adjustments, splits/dividends, missing sessions, benchmark dates, currency and next-session close execution; compare realistic net-of-cost strategy results.
- Reserve an untouched chronological test region *before* tuning; avoid reusing the repeatedly inspected four-stock folds as proof of improvement. Add authentic prospective forecast measurements after the restored DB schema and backups are explicitly reviewed.
- Preserve the original `ai_stock_market` database. Only research read-only queries against `marketpulse_restored_test` were involved in these diagnostics; no schema changes have been applied.

See issue #5 and draft PR #4 for existing release and research gates.

## Code note

The live API currently defaults to the regular `random_forest`, not the research-only Ridge or conservative RF. No promotion is justified by the present evidence.
