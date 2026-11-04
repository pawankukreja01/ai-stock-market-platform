# MarketPulse — Investment research decision quality milestone

## Status

This milestone delivers **research ranking and safer paper allocation**, not a
proven stock-price prediction engine or a personalized investment adviser.
Historical model tests to date have **not** shown consistent improvement
against simple return baselines over multiple stocks. Never market any ranking
score as a probability of profit, forecast accuracy, or expected return.

### What changes

1. Existing market-based, exchange-aware and freshness-gated research ranking
   continues to require stored OHLC prices, a minimum risk-history sample
   and sufficient scoring evidence. Missing research inputs remain missing.
2. Every returned stock now includes:
   - an **evidence-coverage** percentage (available source components divided
     by five), explicitly **not** forecast confidence;
   - price age, risk observation count, fundamentals and sentiment coverage;
   - warnings for absent fundamentals, insufficient news and older prices;
   - transparent component scores and source-availability limitations.
3. The recommendation API defaults to `allocation_method=diversified`.
   This is an **illustrative whole-share paper allocation** with explicit
   **position/sector exposure caps**, not an optimized portfolio. Caps vary by
   risk-preference UI setting:

   | Risk preset | Max one stock | Max one sector |
   |---|---:|---:|
   | Conservative | 15% of budget | 35% |
   | Moderate | 25% | 50% |
   | Aggressive | 35% | 65% |

   Unknown sectors share one conservative bucket; unknown/mismatched
   currencies and invalid share prices are excluded; invested + cash always
   equals budget; cash remains when prices/caps prevent purchase.
4. The legacy rank-first allocator is still accessible via
   `allocation_method=rank_first`, but clearly labeled as concentrated,
   potentially all-in and not the preferred research UX.
5. The Vue recommendations screen displays caps, evidence coverage,
   uncertainty/missing-source warnings and per-stock paper allocation
   percentages.

## What this does NOT establish

- No stock or security has been confirmed as a **profitable buy**.
- Historical source coverage scores are **not** confidence intervals,
  expected returns, win rates, real-time prices, alpha, or a guarantee.
- The system does **not** issue executable orders, brokerage instructions or
  investment advice. No automatic trades.
- The 33-stock Ridge alpha1000 research cohort in draft PR #8 is not an
  independently validated forecasting model; this milestone does **not**
  silently add those experimental returns to investment rankings.
- This work is software/test development only. It cannot verify the user's
  local market-data freshness or browser without access to their Mac.
- Position/sector caps are chosen safety heuristics, not statistically
  optimized asset allocations; correlations and exposures across sectors,
  holdings, countries and currencies still require analysis.

## Remaining gates toward a dependable product

**Data**: add supervised, rate-limited ingestion with provider-specific
freshness/currency/quality checks and clear outages. Validate US and UK
adjustments, dividends, exchange calendars, quote timestamps and stale prices.
Do not bypass Yahoo HTTP 429.

**Prediction evidence**: measure the frozen 33-stock, four-horizon candidate on
a protected future or truly untouched sample; track immutable prospective
forecasts and realized outcomes. Compare stock-level MAE, downside
specificity, balanced direction, uncertainty calibration and costs against
zero-return and other reasonable baselines. Exclude apparent wins that arise
from selection on previously inspected test folds.

**Investment research**: timestamp all inputs, exclude post-as-of company
fundamentals and sentiment, verify out-of-sample historical stock ranking by
point-in-time construction, benchmark against equal-weight, sector and market
indices, calculate turnover, drawdown and risk-adjusted after-cost returns.
Risk limits alone do not create investment alpha.

**Acceptance**: Django test suite, frontend build, browser smoke tests,
localhost preview integration with actual cached data, security review,
explicit terms of market-data access, rate limits, recoverable backups.
No production approval until the tests and real outcomes meet a predefined
evaluation threshold.

## Local smoke test

In a safe review worktree after applying the branch, choose a market with
verified locally cached recent prices, then open Recommendations and select
**Diversified**. Inspect each stock's evidence coverage and warnings and verify
that paper positions obey the displayed caps. If prices are stale or
unavailable, the application should explain why no recommendations are
available; it must not fabricate up-to-date opportunities.
