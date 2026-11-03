# MarketPulse authentication and session security review

## Root cause of the reported incident

Previously the Vue inactivity handler called the logout API and, even
if it failed (network error, CSRF rejection, or an already-expired
session), always redirected to `/login`. That browser redirect **did
not prove Django invalidated its session**. On refresh the route guard
called `/api/auth/me/`, saw the still-valid session cookie and
redirected straight back into the dashboard, without a password.

Two additional contributors were the client timer restarting on each
page reload and `SESSION_SAVE_EVERY_REQUEST=True`, allowing passive
polling and auth checks to extend Django session lifetime.

## Security controls added

- Backend `ServerInactivityMiddleware` enforces 30-minute explicit
  inactivity and an independent 12-hour maximum login lifetime on every
  authenticated request. A page reload, passive GET, API poll, or
  background refresh is not real activity.
- Only a CSRF-protected `POST /api/auth/activity/` extends the idle
  deadline. The Vue client sends it on throttled, genuine user
  interactions. "Stay logged in" explicitly confirms the server renewal.
- GET `/api/auth/me/` returns server-calculated `session.expires_at`
  with `Cache-Control: no-store`; unexpired server session is required
  to enter protected routes.
- POST `/api/auth/logout/` is idempotent and can invalidate an
  authenticated session or return success if already anonymous. It is
  protected by strict Django CSRF and flushes the session.
- Browser signout is **not** considered complete until the logout POST
  and a server response confirming `/auth/me/` is unauthenticated.
  If this cannot be verified, the browser uses a non-sensitive
  cross-tab pending-signout flag to lock protected navigation.
- The session cookie is HttpOnly, has a MarketPulse-specific cookie
  name, and must be Secure outside DEBUG. It contains no stored
  password, and the frontend does not store any access token.
- POST login, logout and other anonymous account mutations use a
  special CSRF proxy. DRF normally marks its API views `csrf_exempt`;
  wrapping that exempt view with ordinary `csrf_protect` was not
  sufficient. An actual browser-style CSRF regression test caught this.
- Only cookie-based SessionAuthentication is enabled for DRF. Implicit
  HTTP Basic authentication is disabled. Login attempts are throttled
  by remote IP, including attempts from existing authenticated users,
  with untrusted forwarded IP headers ignored by default.
- Login errors use generic credentials messages and avoid
  missing-account timing differences where practical. The responsive
  login page offers password visibility, keyboard access, an
  email-verification path, rate-limit notices, and a retry-signout
  action.

## Manual acceptance checklist (against an isolated test deployment)

1. Authenticate, open a private research screen, sign out, refresh,
   and confirm you stay on `/login`. `GET /api/auth/me/` must return
   HTTP 401 or 403. No credentials should be accepted silently.
2. Sign in, remain inactive for at least 30 minutes while the
   dashboard might poll for quotes or alerts, refresh, and confirm the
   server denies access.
3. Remain active for 25+ minutes and use the explicit "Stay logged in"
   button. It must extend the *server* idle deadline; a refresh must
   not extend it on its own.
4. Open two tabs in one browser, log out in one, and confirm the
   other tab blocks protected pages without a reload.
5. Simulate a network error during logout. The app must lock the
   workspace and show a pending-signout notice instead of declaring
   success. Reconnect and retry; refresh must not silently unlock.
6. Verify that anonymous login POST without valid CSRF is rejected.
   Normal login, registration, verification and reset forms obtain a
   CSRF token and function with cookies enabled.
7. Enter incorrect credentials repeatedly; confirm a 429 after the
   configured limit, regardless of forged X-Forwarded-For headers.
8. Confirm keyboard navigation, visible focus, password visibility,
   validation messages and mobile screen widths.
9. Confirm a logged-in session requires re-authentication after the
   absolute maximum (12 hours), even if you have remained active.
10. Verify credentials and profile data are never printed to logs or
    written into localStorage.

## Limitations and production gate

A browser cannot invalidate an unreachable server session; the client
locks itself while awaiting confirmation, but **the backend idle limit
is the authoritative protection**. Browser storage may be disabled or
cleared. When a logout request fails, avoid claiming that all other
devices or stolen session cookies have been revoked.

This fix changes the cookie name and will require existing users to
sign in again. Production requires HTTPS, trusted reverse proxy
configuration, a **shared** rate-limit/cache backend across Gunicorn
workers (a per-process memory cache is insufficient against distributed
brute-force attempts), secure email and password-reset delivery,
security logging, browser-level acceptance testing and independent
penetration review. MFA/passkeys and device-wide session revocation
remain future enhancements, not deployed capabilities.

The work is in an isolated draft security pull request. Tests use
GitHub Actions' disposable PostgreSQL test service; **do not run
schema migrations, refreshes or destructive operations against the
original `ai_stock_market` database or backup.**
