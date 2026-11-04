# Forecast pipeline ablation — measured 2026-11-02 development results

## Evidence provenance

- Source: user-run `pipeline_ablation_5d_20261102.json` from `marketpulse_restored_test`.
- SHA-256: `39957ec8f0516301304a6c077f22cbf0cec779600d7c7cc6e567b655e49f65b9`.
- Cutoff: 2026-11-02; horizon: five trading sessions, next-session close entry, H-session close exit.
- 4 stocks (AAPL, ABF.L, MSFT, NVDA), 18 candidate grids each = 72 evaluations.
- Fixed research inputs: `min_train=500`, `test_size=100`, `--include-market=false`.
- Candidate grid: feature sets `price_volume` versus `price_volume_volatility_normalized`; training windows expanding, rolling 500, rolling 750; zero-anchor Ridge alphas 100, 300, 1000.
- Same forecast test-date ranges and held-out observation counts for every candidate within each stock. AAPL 17 folds / 1700 held-out observations; other stocks 5 folds / 500 held-out observations each.
- The research `cohort_sha256` is null: the exact historical 33-stock cohort still has to be recovered.
- These are **development folds that have already been inspected repeatedly**, NOT independent final evaluation or prospective verification.

## Measured results

| Stock | Strongest simple baseline MAE | Expanding raw-feature Ridge alpha 100 MAE | Expanding raw-feature Ridge alpha 1000 MAE | alpha 1000 balanced direction | alpha 1000 negative specificity |
|---|---:|---:|---:|---:|---:|
| AAPL | 3.11896% | 3.26275% | 3.17169% | 52.326% | 60.083% |
| ABF.L | 2.53573% | 2.71555% | 2.57334% | 52.801% | 19.502% |
| MSFT | 2.98692% | 3.05820% | 3.00953% | 48.081% | 36.889% |
| NVDA | 4.44915% | 4.41811% | 4.39695% | 52.939% | 14.480% |

For this **fixed matched comparison**, stronger regularization reduced MAE on all four stocks, but **only NVDA beat the strongest baseline**. On NVDA the alpha-1000 error gain came with lower negative specificity (14.48%, versus 27.149% at alpha 100); improvements in numeric accuracy do not imply better downside discrimination.

The individually lowest MAE from each stock's *full* 18-way searched grid was:

| Stock | Best MAE across 18 candidates | Feature set | Training window | Ridge alpha | Best simple baseline |
|---|---:|---|---|---:|---:|
| AAPL | 3.17169% | raw price/volume | expanding | 1000 | 3.11896% |
| ABF.L | 2.57334% | raw price/volume | expanding | 1000 | 2.53573% |
| MSFT | 3.00198% | volatility normalized | rolling 500 | 1000 | 2.98482% (window-matched historical mean) |
| NVDA | 4.38639% | volatility normalized | rolling 500 | 1000 | 4.44915% |

**The winning configurations above are post-hoc selected on already-seen test outcomes** and cannot be presented as validated deployment choices.

Across 72 model-stock configurations, 15 beat all three simple baselines on MAE, **all 15 on NVDA using the same set of 500 historical test observations**. These are dependent experiments, not 15 independent forecast trials or evidence of 15 different profitable models.

Volatility normalization reduced MAE in **9/36** directly matched comparisons; the rolling 500-observation window helped **5/24**, and the rolling 750-observation window helped **10/24** relative to expanding on otherwise matched settings. Neither added feature normalization nor rolling retraining showed a generalizable improvement on this four-stock development sample.

## Decision and next tests

1. Preserve the current production `random_forest` default and experimental labeling. No performance claim or production model replacement.
2. Record a frozen regularization hypothesis (e.g. expanding price/volume Ridge alpha=1000) for **future** evaluation. The four-stock experiment generated this hypothesis; it did not validate it.
3. Perform a paired market-feature ablation **only if** same-market US and UK benchmark histories exist locally; no provider fetching, silent benchmark fallback, or alignment mismatches.
4. Recover and fingerprint the exact 33-symbol cohort manifest before the 33-stock study. Evaluate 1, 5, 20 and 60 day horizons, with outcomes and folds explicitly labeled.
5. Reserve a truly untouched chronological test period, report per-fold variation and overlapping versus executable non-overlapping decision events, and investigate whether small observed differences survive proper uncertainty, dividends and trading costs.
6. Observe actual prospective forecasts after user-approved schema/backups; independent data is mandatory before any promotion.

The new `Model Reliability` page includes the ablation summary, matched Alpha 100 versus Alpha 1000 error and downside-specificity comparison, and explicit limitations. Historical interval coverage remains **Not measured**.
