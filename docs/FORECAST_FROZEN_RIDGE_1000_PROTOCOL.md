# Frozen candidate: expanding Ridge α=1000 (research only)

**Frozen November 4, 2026.** Candidate: `ridge-zero-anchor-expanding-alpha1000-price-volume-v1`. Model and feature settings are locked in `backend/market_data/frozen_research_candidate.json` and checked against `FROZEN_SPEC` in `frozen_research_candidate.py`. A settings drift is rejected, not automatically adopted.

## Exact protocol
- Model: zero-anchor Ridge `alpha=1000`, `fit_intercept=False`, median imputation and standard scaling fit on training folds **only**.
- Features: original `price_volume` set only, no added benchmark features or normalized return features.
- Training: expanding, `min_train=500`, `test_size=100`, `step_size=100`, chronological unshuffled folds with `H+1` label purge.
- Target: `C[t+H+1] / C[t+1] - 1`; unadjusted close price, excludes dividends, fees, slippage and taxes.
- Horizons: 1, 5, 20 and 60 trading sessions, evaluated against zero-return, per-fold historical mean and momentum on matching origins.
- **Not approved**: production model change, investment claims or trading recommendation.

The candidate was chosen after repeatedly inspecting the 2026-11-02 four-stock development data. It is a **hypothesis**, not independently verified accuracy. On those already-inspected observations, alpha=1000 reduced MAE in the fixed expanding-window comparison for all four, but only NVDA beat the strongest baseline and its negative specificity fell to about 14.48%.

## Locked 33-stock validation

**Recovered and verified 2026-11-04.** The original owner's `raw_vs_adjusted_33_stock_report.json` was uploaded and its `configuration.symbols` list checked against `preflight.results` (same exact ordered sequence), `stocks` keys, uniqueness, and success flags. The source reports 33/33 processed, 33/33 aligned, and 0 preflight errors.

- Verified report SHA-256: `c3943426966a282eb5342e12a4b6e9f3ca7453cabc8ba693490f908e52acc745`.
- Source configuration: five-session forecast, minimum train 400, test size/step 80, purge gap **5**. This is **not** the new frozen study's train 500, step 100 and H+1-row purge.
- Original 33 tickers now committed in `backend/market_data/research_cohorts/raw_adjusted_33_stock_v1.json`; SHA-256: `8ceac6b8b1d1ada47a719f97ab29c398696d1b28211c27523e7d963d4739e345`.
- Exchange coverage: 12 LSE, 11 NYSE and 10 NASDAQ. The original preflight is evidence of source alignment **under its old protocol**, not evidence that every stock has the 3+ purged folds needed at each of the new four horizons.
- Do not fabricate replacements for any excluded symbols. In particular SVT.L had 686 usable rows in the prior report, which may limit valid folds.

If using the repository version of the manifest, pass `--cohort-file market_data/research_cohorts/raw_adjusted_33_stock_v1.json` while in `backend/`. The file is committed as a research input, **not** a stock recommendation.

In the new worktree after fetching/checking out this PR's branch:

```bash
cd ~/Desktop/ai-stock-market-platform-research
git fetch origin research/frozen-ridge-1000-33stock-validation
git switch --detach origin/research/frozen-ridge-1000-33stock-validation
cd backend

DB_NAME=marketpulse_restored_test \
~/Desktop/ai-stock-market-platform/.venv/bin/python \
manage.py validate_frozen_forecast_candidate \
  --cohort-file market_data/research_cohorts/raw_adjusted_33_stock_v1.json \
  --as-of 2026-11-02 \
  --output ~/Desktop/marketpulse_model_evaluation/frozen_ridge1000_33stock_20261102.json
```

The command:
1. Refuses all DBs except the explicitly configured **and connected** `marketpulse_restored_test`.
2. Refuses a changed model lock, a missing or non-33-symbol cohort, missing/inactive catalogue tickers and an existing output file.
3. Uses one **common calendar window** for the 33 selected stocks, with stock-specific missing-session/feature exclusions.
4. Reports 33 × 4 candidate evaluations where data is sufficient, requiring at least three purged folds per stock/horizon; otherwise reports the exclusion.
5. Saves stock/horizon fold diagnostics, model metrics and all three baselines, candidate/cohort SHA-256, and a non-deployment warning.
6. Does **not** mutate a DB, change production forecasts, call Yahoo, or migrate anything.

## Important remaining validity gates

Because the candidate was chosen from inspected data, its 33-stock historical results are still **development diagnostics**, not an untouched final validation period. Before promoting a model:
- Pre-register a new untouched future period or prospectively capture immutable forecasts and actual observed returns, then check sample counts, MAE relative to each baseline, balanced directional accuracy, downside specificity and uncertainty calibration.
- Audit stock split and dividend return bases, benchmark alignment, invalid OHLCV, liquidity and market-regime sensitivity.
- Report overlapping vs executable non-overlapping horizon decisions and net transaction costs.
- Check performance across markets, sectors, stocks and folds; do not pick model settings post hoc from the new research sample and call the same sample validation.

The live `random_forest` API remains unchanged. The PR stacks on PR #7 and should not be merged until CI and human code review pass.
