# MarketPulse browser acceptance tests

These Playwright tests are an **opt-in** release-candidate check; they are not
part of the standard GitHub CI quality workflow and have not been presented
as having passed. Run only against the isolated Docker preview database.

1. Follow `docs/DEPLOYMENT.md` to start the Docker preview on port 8088,
   run migrations in its isolated database, and create a dedicated test user.
2. `cd e2e && npm install && npx playwright install chromium`
3. `MARKETPULSE_BASE_URL=http://127.0.0.1:8088 npm test`
4. For logged-in journeys, additionally set
   `MARKETPULSE_E2E_EMAIL` and `MARKETPULSE_E2E_PASSWORD` for that
   **disposable preview account only**.

No test should ever be run with a production URL, real user credentials,
or the original local `ai_stock_market` database. The browser suite
cannot establish exchange market-data accuracy or ML predictive skill.


## Automated isolated CI browser gate

The quality workflow now provisions its own **disposable** PostgreSQL service
(`marketpulse_e2e_ci`), applies migrations only there, creates a test-only
account and starts Django/Vite on loopback. Desktop and mobile Chromium run
against the real session/CSRF endpoints without Yahoo requests or any user's
original database. The login credentials in that job are intentionally
throwaway and must never be reused outside CI.

Browser tests include sign-in, protected page refresh, server-side logout
confirmation, cross-tab sign-out and anonymous route behavior. Session
expiry at 30 minutes / 12 hours remains covered by Django's clock-controlled
regression tests rather than waiting for real clock time during CI.

If the browser job fails, inspect GitHub's CI logs and short-lived Playwright
traces. **A green CI gate does not replace** review of deployment secrets,
HTTPS, shared rate limiting, backup restore, or third-party data rights.
