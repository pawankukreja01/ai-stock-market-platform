# MarketPulse — Full Project Review Checklist

This checklist is for reviewing the current research-platform development
branch **before merging or deploying**. It complements the main README.

## Scope of the working application

- Django REST API with PostgreSQL, account registration/login, email
  verification and password reset, authenticated user profile.
- Vue 3 responsive workspace: Dashboard, Stock Discovery, Stock Research,
  Screener, Portfolio, Investment Simulator, Alerts, and Recommendations.
- Read-only stored-data Research Health page at `/research-health`, exposing
  OHLC data-quality flags, quote source freshness, annual/quarterly statement
  coverage, and stored news availability.
- Research-only forecast and explainability endpoints, historical simulator,
  and leakage-aware model evaluation against simple baselines.
- Read-only data consistency and walk-forward audits.
- Controlled historical price ingestion with `--dry-run` and revision guard.

**Critical limitation:** The observed ML forecasts have not consistently
outperformed zero-return, historical-average and momentum baselines. No output
is guaranteed or suitable for live trading, and this application places no
trades. Yahoo Finance can rate-limit or change data; absence of fresh data
should be displayed as absence or stale, never fabricated.

## Non-destructive local evaluation

Do not delete, reset, truncate, migrate or update the original local
`ai_stock_market` database. Keep the original database dump and the three
pre-existing untracked files unchanged. For local Django commands that need
real stored data, use **only** `DB_NAME=marketpulse_restored_test`.

```bash
cd ~/Desktop/ai-stock-market-platform
git status --short --branch
cd backend
DB_NAME=marketpulse_restored_test python manage.py check
DB_NAME=marketpulse_restored_test python manage.py makemigrations --check --dry-run
DB_NAME=marketpulse_restored_test python manage.py audit_research_health --symbols AAPL MSFT NVDA ABF.L
DB_NAME=marketpulse_restored_test python manage.py audit_prediction_prices --symbols AAPL MSFT NVDA ABF.L
```

Django's `manage.py test` creates an isolated test database. Confirm the
database name/configuration in your environment before running it on your Mac;
GitHub CI already runs its tests on a disposable PostgreSQL container.

To build/test the Vue frontend:

```bash
cd ~/Desktop/ai-stock-market-platform/frontend
npm ci
npm test
npm run build
```

To run the project locally, start Django using the restored database in one
terminal and Vite in another. Follow the main README for installed packages,
credentials, authentication, and development ports. Do not run
`ingest_stock_history`, `backfill_stock_history`, bulk refresh or
`sync_personal_research --execute` for this read-only review.

## Manual browser acceptance

1. **Authentication:** Guest routes redirect correctly, login succeeds,
   logout invalidates session, profile updates require CSRF, inactivity
   timeout behaves as described.
2. **Navigation and accessibility:** All sidebar links work at desktop and
   mobile widths; tab order, focus indicators, error messages, and forms
   remain readable.
3. **Dashboard:** Quote source timestamps and freshness state are explicit;
   missing stock/news data is not presented as zero or as live market data.
4. **Stock Research:** US stocks use S&P 500 (^GSPC) and London stocks use
   FTSE 100 (^FTSE) for relevant comparisons; each price is displayed in
   its own currency; missing quarterly fundamentals are labeled unavailable.
5. **Research Health:** Only signed-in users can access
   `/api/research-readiness/`; blank selection checks the first 12 active
   symbols; comma-separated valid symbols filter results; invalid or missing
   symbols show an error; missing quotes are labeled correctly.
6. **Portfolio and Alerts:** Existing owners alone can read/write their
   portfolios, holdings, alert rules and events; check empty states and
   validation errors; use separate test accounts in an isolated environment.
7. **Recommendations:** Rankings and allocation remain research-only,
   clearly state their evidence/limitations, and do not invent forecast
   accuracy or guarantee performance.
8. **Provider outage:** With Yahoo unavailable, stored-data pages remain
   readable; refreshing should not silently clear valid locally stored
   research records.

## Data quality and provider safeguards

A previous ABF.L adjusted-close discontinuity was observed around
2021-11-01. Different Yahoo `repair` modes returned different
historical factors. This is **not** conclusive evidence of an actual
corporate action or of a specific earlier import mistake.

Historical re-ingestion now checks material adjusted/close-factor revisions
and large jumps in the *incoming* factor series before writing records.
`--dry-run` is a no-write preview; normal execution refuses large
adjustment revisions without explicit authorization. Smaller corrections
can still overwrite existing values. Exercise care, preserve a backup,
and never use the original local database for review.

Yahoo returned HTTP 429 on a recent diagnostic attempt. Avoid repeated
requests and do not bypass rate limits. Connectivity and latest-provider
integration remain unverified until the provider is available.

## Quality gates and release conditions

- GitHub Actions runs Django system checks, model migration consistency,
  the backend test suite on an **ephemeral CI PostgreSQL database**,
  frontend Node-based logic tests, and a Vite production build.
- The current draft PR should be reviewed with **all CI jobs passing on
  its latest head SHA** before any merge.
- Real login-to-browser end-to-end automation and a real deployment smoke
  test are separate from these automated unit/integration tests.
- Configure production Django secrets, trusted origins, email delivery,
  static-file hosting, HTTPS proxy headers, backups, observability,
  and an authorized data-provider arrangement before public deployment.
- Independent prospective validation is required before describing any
  forecast as demonstrating reliable predictive advantage.

## Review and merge

All changes are kept on `feature/launch-security-and-beginner-ux` in a
draft pull request. **Nothing is merged or deployed automatically** by
this review workflow. Inspect the diff, tests, and app behavior first.
