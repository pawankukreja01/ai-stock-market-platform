# Trustworthy research data: timestamp guards + historic ranking replay

## Status
Development-only safeguards; no forecast model is promoted and no investment return accuracy is claimed.

### 1. Prevent historical look-ahead

`extract_candidate_features(stock, as_of=...)` now uses:
- price and risk observations dated on/before `as_of`;
- fundamentals with a non-null fiscal `period_end <= as_of` **and** actual stored
  ingestion `created_at <= as_of`; late-backfilled and unknown-period records
  are excluded from earlier evaluations;
- news sentiment only if `published_at`, `retrieved_at`, and
  `sentiment_analyzed_at` all precede the evaluation date;
- explicit evidence cutoff and original filing-date limitations.

**Important:** `period_end` does not prove when filings first became public.
The created-at gate is a conservative first safeguard, not a certified
point-in-time fundamentals vendor feed. An archive transferred later will
appear unavailable to prior historical snapshots. Do not invent past evidence.

### 2. Research-only ranking replay

A new read-only management command evaluates whether the **current provisional
ranking heuristic** would historically have shortlisted stocks that outperformed
the equal-weight **ranked eligible** cohort over a fixed future horizon.

To avoid selection bias from missing outcomes, a period is **excluded entirely**
when even one scored stock has insufficient future valid closes. Returns are
the next stored close through the H-session exit (no same-close fills).
Both long-only arms are charged the same round-trip assumed cost in bps.
The per-period baseline win rate is **not** a probability of a profitable trade,
a statistical confidence interval, nor independently validated alpha.

Use an explicit 2–100 symbol JSON cohort `{"symbols":["AAPL","MSFT",...]}`,
preferably the previously recovered 33-stock cohort. The study is fully
offline and checks that both the `DB_NAME` environment and actual Django
DB connection equal `marketpulse_restored_test` before any data access.

Example, from the research branch's `backend/` folder:

```bash
DB_NAME=marketpulse_restored_test \
python manage.py replay_recommendation_rankings \
  --cohort-file market_data/research_cohorts/raw_adjusted_33_stock_v1.json \
  --start-date 2024-01-01 --end-date 2026-04-01 \
  --horizon 20 --calendar-step 30 --top-k 5 \
  --risk moderate --horizon-months 12 \
  --cost-bps-per-side 10 \
  --output ../marketpulse_model_evaluation/ranking_replay_research.json
```

**Note:** The manifest shown lives in the separate PR #8 branch and is not
automatically included in this PR. Either provide the existing original
local file via `--cohort-file`, or incorporate PR #8's exact manifest
after reviewing it. The command never guesses missing symbols.
Do not run it on `ai_stock_market`, and never overwrite research results.

### 3. Interpretation and known limits

- Fixed historical study using today's stock list and active flags suffers
  survivorship / historical-universe selection bias.
- Historical sources have incomplete original publication timestamps.
- Trading day and rebalance dates differ across US/UK exchanges; no
  exchange-specific holiday calendar or realistic order execution is modeled.
- Unadjusted closes omit dividends, FX, bid/ask spreads, market impact and
  tax. Fixed round-trip fees alone do not represent true trading costs.
- A signal may occur on an exchange holiday; `as_of` uses the latest
  eligible stored close, with dates disclosed by the underlying ranking.
- Report measures a historical top-k equal-weight diagnostic, **not** the
  production diversified paper portfolio's executable performance.
- The existing 33-stock Ridge study and four-stock benchmark were repeatedly
  inspected; none constitutes an untouched holdout.
- A trustworthy public-facing performance scorecard still requires immutable
  pre-outcome signals, enough future outcomes, genuine benchmark comparison,
  realistic adjusted total returns and data-source governance.

### 4. Required tests and production posture

Django tests cover future period-end, post-cutoff ingestion, news sentiment,
H+1 return calculation, missing-outcome exclusion and original-DB refusal.
No schema migrations, live ML settings, market-provider calls, brokerage orders,
or user account records are modified. PRs remain drafts until complete CI and
local browser verification succeed.
