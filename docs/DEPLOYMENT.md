# MarketPulse release-candidate deployment and operations

**Status:** Containerized **local preview only**, not a completed public
production deployment. A public launch needs separate infrastructure,
authorization, credentials, backups, observability, and acceptance.

## Isolated Docker preview

The `compose.preview.yml` stack creates a dedicated **new** PostgreSQL
volume and database called `marketpulse_preview`. It does not mount
`ai_stock_market`, `marketpulse_restored_test`, or any local SQL dump.
Never use this preview file to attach a production database.

1. Inspect `compose.preview.yml` and `preview.env.example`.
2. Copy `preview.env.example` to an ignored file called `preview.env`.
   Replace both placeholder secrets with unique random values.
3. Start isolated preview:
   `docker compose --env-file preview.env -f compose.preview.yml up --build -d`.
4. Apply schema **only within that fresh Docker database**:
   `docker compose --env-file preview.env -f compose.preview.yml exec backend python manage.py migrate`.
5. Open `http://127.0.0.1:8088`; for manual user acceptance, create
   disposable preview-only credentials using
   `docker compose --env-file preview.env -f compose.preview.yml exec backend python manage.py createsuperuser`.
6. Exercise registration, login, portfolio, research health and prospective
   scorecard in a browser. Empty market data and zero forecast outcomes
   are expected until opt-in preview-only data seeding is performed.
7. Stop with
   `docker compose --env-file preview.env -f compose.preview.yml down`
   **without** `-v` to preserve preview data. To remove preview data
   deliberately, explicitly approve and inspect volume names first.

The frontend Nginx configuration keeps the Django API under a single origin,
so session auth and CSRF avoid cross-origin cookie problems in the preview.
Production user-uploaded media is **not** served by this stack (Nginx returns
404 for /media); configure an authorized external media storage service
with access controls before deployment. Email goes to console, not to users.

Docker images, including large ML model dependencies, have not been
reproduced on the user's host by this code-only work. Do not call this
a production deployment or a verified browser release yet.

## Production prerequisites

- Domain and HTTPS certificate; trusted reverse proxy; controlled forwarding
  of `X-Forwarded-Proto`; `DJANGO_DEBUG=false`; secret key from a managed
  secret store, not a tracked .env; explicit allowed hosts and CSRF origins.
- Managed PostgreSQL with restricted app role, TLS, encrypted off-site backups,
  point-in-time recovery, retention and demonstrated restore; never reuse
  personal databases or original local dumps.
- Object storage/CDN for profile/media uploads, separate from WhiteNoise
  static assets. Scan and validate uploads and configure quotas.
- Production SMTP transactional service for verification and password reset.
- Persistent caching, bounded background workers and supervised schedules for
  allowed price/news refreshes; obey provider access restrictions and rate
  limits; never bypass a provider-imposed 429.
- Metrics, error reporting, structured logs with secret redaction, alerting on
  failure/backlog and quote freshness; owner notifications for incidents.
- Rollback plan, staging smoke test, database migration preview and backup
  before any production schema changes.
- Dependency vulnerability review, OWASP authentication/access checks,
  accessibility audit and legal review of market-data rights and financial
  risk disclosures.

## Deployment gate checklist

Run GitHub CI on the exact release SHA. The CI suite checks Django migrations,
Django unit/integration tests, frontend logic tests and Vite production build.
Then run the opt-in Playwright tests in `e2e/` against an isolated preview
server, with a dedicated disposable account. Perform a backup and **restore**
drill of the isolated preview database, then staging smoke tests with HTTPS,
email, media, logout/session expiry and data-provider outage simulation.

Do not merge new release-candidate changes or deploy to public users until
both automated and manual gates are approved. Experimental model results
must be identified as unverified unless true future outcomes support the
claims. This system does not execute live trades.

## Rollback & incident response

For a backend regression, keep a tagged known-good application release
available, stop write-capable market data jobs, take a snapshot, and restore
the old application image. Do **not** roll back a database migration
without a tested reverse migration and a recoverable snapshot. If provider
rate limiting occurs, halt jobs, show last stored quote and source
timestamp, and resume only after access is restored and allowed.

For incidents involving personal user information, disable affected access
paths, collect redacted logs, evaluate notification/legal duties and rotate
exposed secrets.
