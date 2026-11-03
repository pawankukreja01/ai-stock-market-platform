# MarketPulse v1.0 beta and owner handover

This is a **beta-release checklist**, not evidence that a public release
has occurred. The owner must approve each gate and verify the behavior
in an isolated environment before inviting real users.

## Seven-milestone status

1. Provider resilience: implemented fail-fast HTTP 429 handling for quotes,
   bulk sync and monitor; mock-based regression tests. Provider availability
   and licensing remain external.
2. Data pipeline: historical ingest dry-run and large adjustment revision
   guard; read-only research data audits, currency provenance, safe offline
   checks. Automatic scheduling and corporate-action reconciliation need
   a trusted provider and operator approval.
3. AI validation: issue server-generated forecasts intentionally into
   a dedicated prospective journal; score only after a future full holding
   period is observed; compare against zero-return baseline. No future
   outcomes are invented. Independent predictive edge is **unproven**.
4. UX: authenticated Dashboard, Getting Started, Stock Discovery and
   Research, Recommendations, Portfolio, Alerts, Investment Simulator,
   Research Health and Forecast Performance views. Manual user testing
   needed for different viewport sizes and assistive technologies.
5. Test/security: Django integration tests, frontend Node tests, Vite
   build in CI; opt-in Playwright desktop/mobile browser acceptance suite.
   External security review and live-browser acceptance outstanding.
6. Deployment: Docker-based isolated preview and documented Nginx,
   Gunicorn and static assets. Public hosting, HTTPS, SMTP,
   media storage, backups and monitoring must be configured separately.
7. Launch: beta script and operational handover are prepared, but
   **no beta participants were invited** and no live deployment performed.

## Acceptance process

- Confirm all automated jobs pass on the exact PR head SHA.
- Review the complete diff for security, performance and accidental writes.
- Run isolated preview migrations, auth flows and Playwright smoke tests.
- Verify asset loading, responsive navigation and error messaging.
- Demonstrate read-only research when Yahoo is unavailable and preserve
  stored quote source timestamps after 429.
- Verify user-owned portfolios/alerts cannot be accessed by other users.
- Evaluate a forecast issued before its next-session entry only after the
  future exit actually occurs; compare to contemporaneous zero baseline.
- Review data-provider terms, marketing claims, legal disclosure and privacy.
- Test restore from database backup and rolling back the application.
- Create a release tag and deployment rollback reference on approval.

## Beta-feedback record

Collect and triage: issue title, affected screen, reproducible steps,
browser/OS, user-visible impact, severity, evidence (without secrets),
and assigned resolution. Block release on high-severity auth/data leakage,
data corruption, and forecasts mislabeled as validated or real-time.

## Handover deliverables

Repository + README, `docs/REVIEW_CHECKLIST.md`, `docs/DEPLOYMENT.md`,
this document, GitHub Actions logs, `e2e/` smoke suite,
`/research-health` and `/forecast-performance` screens and the
opt-in prospective settlement command. Local original PostgreSQL
databases and the original dump are outside project tooling and must
not be modified during this review.
